# Ensure _data directory exists
New-Item -ItemType Directory -Force -Path .\_data | Out-Null

# Fetch Substack RSS feed with browser-like User-Agent
Invoke-WebRequest `
  -Uri "https://valentinguigon.substack.com/feed" `
  -Headers @{
    "User-Agent" = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/121.0.0.0 Safari/537.36"
  } `
  -OutFile ".\_data\substack_feed.xml" `
  -UseBasicParsing

# Display first 10 lines for sanity check
Get-Content -Path ".\_data\substack_feed.xml" -TotalCount 10
