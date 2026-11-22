"""Minimal stdlib client for the ComfyUI HTTP API (upload, queue, wait, download)."""

import json
import mimetypes
import os
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid


class ComfyError(RuntimeError):
    pass


class Comfy:
    def __init__(self, base_url: str, timeout: float = 30.0):
        self.base = base_url.rstrip('/')
        self.timeout = timeout
        self.client_id = uuid.uuid4().hex

    # --- low level -------------------------------------------------------------------------------------------
    def _req(self, path, data=None, headers=None, method=None, raw=False):
        req = urllib.request.Request(self.base + path, data=data, headers=headers or {}, method=method)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                body = r.read()
        except urllib.error.HTTPError as e:
            raise ComfyError(f'{method or "GET"} {path} -> HTTP {e.code}: {e.read().decode(errors="replace")[:4000]}')
        except urllib.error.URLError as e:
            raise ComfyError(f'cannot reach ComfyUI at {self.base} ({e.reason}); start it with: bash scripts/serve.sh')
        return body if raw else json.loads(body or b'null')

    def get(self, path):
        return self._req(path)

    def post_json(self, path, obj):
        return self._req(path, json.dumps(obj).encode(), {'Content-Type': 'application/json'}, 'POST')

    # --- API -------------------------------------------------------------------------------------------------
    def alive(self) -> bool:
        try:
            self.get('/system_stats')
            return True
        except ComfyError:
            return False

    def system_stats(self):
        return self.get('/system_stats')

    def object_info(self, node_class: str | None = None) -> dict:
        path = '/object_info' + ('/' + urllib.parse.quote(node_class) if node_class else '')
        return self.get(path)

    def choices(self, node_class: str, input_name: str) -> list[str]:
        """Allowed values of a combo input (e.g. the model files a loader can see)."""
        info = self.object_info(node_class).get(node_class)
        if not info:
            raise ComfyError(f'node {node_class!r} not registered; is ComfyUI-piFlow installed? (bash scripts/setup.sh)')
        spec = info['input'].get('required', {}).get(input_name) or info['input'].get('optional', {}).get(input_name)
        if spec is None:
            return []
        if isinstance(spec[0], list):
            return spec[0]
        return (spec[1] or {}).get('options', []) if len(spec) > 1 else []

    def upload_image(self, path: str) -> str:
        """Upload a local image to ComfyUI's input dir; returns the name to use in LoadImage."""
        boundary = uuid.uuid4().hex
        name = os.path.basename(path)
        ctype = mimetypes.guess_type(name)[0] or 'application/octet-stream'
        with open(path, 'rb') as f:
            content = f.read()
        parts = [
            f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="{name}"\r\n'
            f'Content-Type: {ctype}\r\n\r\n'.encode() + content + b'\r\n',
            f'--{boundary}\r\nContent-Disposition: form-data; name="overwrite"\r\n\r\ntrue\r\n'.encode(),
            f'--{boundary}\r\nContent-Disposition: form-data; name="subfolder"\r\n\r\nh3gen\r\n'.encode(),
            f'--{boundary}--\r\n'.encode(),
        ]
        res = self._req('/upload/image', b''.join(parts),
                        {'Content-Type': f'multipart/form-data; boundary={boundary}'}, 'POST')
        return f"{res['subfolder']}/{res['name']}" if res.get('subfolder') else res['name']

    def queue(self, graph: dict) -> str:
        res = self.post_json('/prompt', {'prompt': graph, 'client_id': self.client_id})
        if res.get('node_errors'):
            raise ComfyError('graph rejected: ' + json.dumps(res['node_errors'], indent=1)[:4000])
        return res['prompt_id']

    def wait(self, prompt_id: str, timeout: float = 3600.0, poll: float = 2.0, on_tick=None) -> dict:
        """Poll /history until the prompt finishes. Returns its history entry; raises on execution error."""
        t0 = time.time()
        while True:
            hist = self.get(f'/history/{prompt_id}')
            entry = hist.get(prompt_id) if hist else None
            if entry and entry.get('status', {}).get('completed') is not None:
                status = entry['status']
                if status.get('status_str') == 'error' or not status.get('completed'):
                    msgs = [m for m in status.get('messages', []) if m[0] == 'execution_error']
                    detail = msgs[-1][1] if msgs else status
                    if isinstance(detail, dict):
                        detail = {k: detail.get(k) for k in ('node_id', 'node_type', 'exception_type',
                                                              'exception_message', 'traceback')}
                    raise ComfyError('execution failed: ' + json.dumps(detail, indent=1, default=str)[:6000])
                return entry
            if time.time() - t0 > timeout:
                raise ComfyError(f'timed out after {timeout:.0f}s waiting for {prompt_id}')
            if on_tick:
                on_tick(time.time() - t0)
            time.sleep(poll)

    def interrupt(self):
        self._req('/interrupt', b'', method='POST')

    def download(self, file_info: dict, dest: str):
        q = urllib.parse.urlencode({k: file_info.get(k, '') for k in ('filename', 'subfolder', 'type')})
        data = self._req('/view?' + q, raw=True)
        os.makedirs(os.path.dirname(os.path.abspath(dest)), exist_ok=True)
        with open(dest, 'wb') as f:
            f.write(data)


def output_files(history_entry: dict) -> list[dict]:
    """All file records ({filename, subfolder, type}) in a history entry's outputs."""
    found = []

    def walk(x):
        if isinstance(x, dict):
            if 'filename' in x and 'type' in x:
                found.append(x)
            else:
                for v in x.values():
                    walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)

    walk(history_entry.get('outputs', {}))
    return found


def execution_seconds(history_entry: dict) -> float | None:
    """Server-side run time from the execution_start/execution_success timestamps."""
    ts = {m[0]: m[1].get('timestamp') for m in history_entry.get('status', {}).get('messages', [])
          if isinstance(m[1], dict)}
    if ts.get('execution_start') and ts.get('execution_success'):
        return (ts['execution_success'] - ts['execution_start']) / 1000.0
    return None
