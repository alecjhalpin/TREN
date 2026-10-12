# Use Tren from your iPhone

First get chat working on your PC with setup.bat and start.bat.

1. Install **Tailscale** on Windows: https://tailscale.com/download/windows
2. Install the Tailscale iPhone app from the App Store. Sign into the **same Tailscale account** on PC and phone. Enable its VPN connection on the phone. Review the available personal plan during setup.
3. On the PC, open PowerShell and run:

   ```powershell
   tailscale serve --bg http://127.0.0.1:8765
   ```

   If the command is not found, use:

   ```powershell
   & "$env:ProgramFiles\Tailscale\tailscale.exe" serve --bg http://127.0.0.1:8765
   ```

4. If prompted, open the link printed by Tailscale to enable HTTPS/Serve. Follow its setup prompt, then rerun the command if requested.
5. It will show a private HTTPS URL, such as `https://my-pc.example-tailnet.ts.net`. **Use the URL it actually prints.** This example will not work for you.
6. Open `allowed-hosts.txt` from the assistant folder in Notepad. Add just that hostname on its own line, e.g. `my-pc.example-tailnet.ts.net`, without `https://` or a trailing slash. If Tailscale prints a nonstandard port, include the port in the allowed entry.
7. Stop Tren with Ctrl+C in its terminal and reopen start.bat. Do not stop Tailscale.
8. On your phone, while Tailscale is connected, open the private HTTPS URL in Safari. Enter the pairing code printed in the PC terminal.
9. In Safari’s Share menu, choose **Add to Home Screen** for an app-like shortcut. It still needs your PC online.
10. Test away from home: turn off phone Wi-Fi, keep cellular data and Tailscale on, and send a message. The PC remains awake and connected to the internet.

Use **Serve**, which is private to your Tailscale network. Do not use **Funnel**, which publishes a service to the internet. Do not forward router ports or expose the Ollama API directly.

To disable this private phone endpoint later, run:

```powershell
tailscale serve reset
```

This resets the PC’s Serve configuration, including any other Serve routes you may have configured. If you already use Serve for other apps, review `tailscale serve status` before changing the configuration above.

Native phone packaging, push notifications and voice are future features. The browser interface shows results when opened; private phone acceptance remains pending.
