# Cloudflare Tunnel Configuration for Sky

## Purpose

This document contains setup notes and configuration for exposing Sky's API via Cloudflare Tunnel, allowing secure remote access without exposing ports or using dynamic DNS.

## Tunnel Setup (To Be Configured)

### Step 1: Create Tunnel

```bash
cloudflared tunnel create sky-agent
```

This will generate:
- Tunnel UUID (paste below)
- Credentials file (keep secure)

### Step 2: Configure DNS

Point subdomain to tunnel:
```bash
cloudflared tunnel route dns sky-agent sky.alex-blythe.com
```

### Step 3: Configure Tunnel

Create `config.yml` for cloudflared:

```yaml
tunnel: <TUNNEL_UUID>
credentials-file: /path/to/credentials.json

ingress:
  # Sky API
  - hostname: sky.alex-blythe.com
    service: http://localhost:5000

  # Catch-all rule (required)
  - service: http_status:404
```

### Step 4: Run Tunnel

```bash
cloudflared tunnel run sky-agent
```

## Tunnel Information

**Tunnel UUID:** `[TO BE FILLED IN]`

**Tunnel Name:** `sky-agent`

**Hostname:** `sky.alex-blythe.com`

**Local Service:** `http://localhost:5000`

**Credentials Location:** `[TO BE FILLED IN]`

## Security Notes

- Tunnel uses mutual TLS authentication
- No inbound ports need to be opened
- All traffic encrypted via Cloudflare
- Credentials file must be kept secure (DO NOT commit to git)

## Running as Service

### Windows (NSSM)

```bash
nssm install CloudflaredSky "C:\Program Files\cloudflared\cloudflared.exe" "tunnel run sky-agent"
nssm start CloudflaredSky
```

### Linux (systemd)

```ini
[Unit]
Description=Cloudflare Tunnel for Sky Agent
After=network.target

[Service]
Type=simple
User=alex
ExecStart=/usr/local/bin/cloudflared tunnel run sky-agent
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable cloudflared-sky
sudo systemctl start cloudflared-sky
```

## Health Checks

Check tunnel status:
```bash
cloudflared tunnel info sky-agent
```

Test endpoint:
```bash
curl https://sky.alex-blythe.com/health
```

Expected response:
```json
{
  "status": "online",
  "agent": "Sky",
  "version": "0.1",
  "phase": "Phase 0 → Phase 1"
}
```

## Troubleshooting

### Tunnel won't start
- Check credentials file path
- Verify tunnel UUID matches config
- Check cloudflared logs

### Can't reach subdomain
- Verify DNS propagation: `nslookup sky.alex-blythe.com`
- Check tunnel is running: `cloudflared tunnel info`
- Verify local service is up: `curl http://localhost:5000/health`

### SSL errors
- Ensure Cloudflare SSL mode is "Full" or "Full (strict)"
- Check certificate validity

## References

- [Cloudflare Tunnel Docs](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/)
- [Configuration Reference](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/configuration/)
