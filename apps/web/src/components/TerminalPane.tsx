import { useEffect, useRef } from 'react';
import { Terminal } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import '@xterm/xterm/css/xterm.css';
import { getToken, wsBase } from '../lib/auth';

/**
 * Live terminal for one lab node. Connects to the console WebSocket proxy
 * (/ws/console/{session}/{node}) and streams keystrokes/output.
 * Reconnect is a fresh attach; the proxy reaps the previous process.
 */
export default function TerminalPane({
  sessionId,
  node,
  observer = false,
}: {
  sessionId: string;
  node: string;
  observer?: boolean;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const termRef = useRef<Terminal | null>(null);

  useEffect(() => {
    const term = new Terminal({
      cursorBlink: true,
      fontSize: 13,
      theme: { background: '#000000', foreground: '#e5e7eb' },
    });
    const fit = new FitAddon();
    term.loadAddon(fit);
    term.open(containerRef.current!);
    fit.fit();
    termRef.current = term;

    const token = getToken();
    const url =
      `${wsBase()}/ws/console/${sessionId}/${node}?token=${token ?? ''}` +
      (observer ? '&observer=1' : '');
    const ws = new WebSocket(url);
    ws.onopen = () => term.writeln(`\r\n--- connected to ${node} ---\r\n`);
    ws.onmessage = (event) => {
      try {
        const frame = JSON.parse(event.data);
        if (frame.type === 'output') term.write(frame.data);
        if (frame.type === 'status') term.writeln(`\r\n[${frame.state}]\r\n`);
      } catch {
        term.write(event.data);
      }
    };
    ws.onclose = () => term.writeln('\r\n--- console closed ---\r\n');
    const disposeInput = term.onData((data) => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'input', data }));
      }
    });
    const onResize = () => fit.fit();
    window.addEventListener('resize', onResize);

    return () => {
      window.removeEventListener('resize', onResize);
      disposeInput.dispose();
      ws.close();
      term.dispose();
      termRef.current = null;
    };
  }, [sessionId, node, observer]);

  return <div className="terminal-wrap" ref={containerRef} />;
}
