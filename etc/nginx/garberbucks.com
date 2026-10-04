server {
    server_name garberbucks.com;

    # s2's etc/nginx/conf.d/fake-chrome.conf: Chrome UA with no Accept-Language.
    if ($fake_chrome) {
        return 403;
    }

    location = /robots.txt {
        default_type text/plain;
        return 200 "User-agent: Amazonbot\nDisallow: /\n\nUser-agent: Amzn-SearchBot\nDisallow: /\n\nUser-agent: Bytespider\nDisallow: /\n\nUser-agent: TikTokSpider\nDisallow: /\n\nUser-agent: SemrushBot\nDisallow: /\n\nUser-agent: ShapBot\nDisallow: /\n\nUser-agent: meta-externalagent\nDisallow: /\n\nUser-agent: DataForSeoBot\nDisallow: /\n\nUser-agent: AhrefsBot\nDisallow: /\n\nUser-agent: MJ12bot\nDisallow: /\n\nUser-agent: PetalBot\nCrawl-delay: 10\n\nUser-agent: ClaudeBot\nCrawl-delay: 10\n\nUser-agent: GPTBot\nCrawl-delay: 10\n\nUser-agent: PerplexityBot\nCrawl-delay: 10\n\nUser-agent: Reflectionbot\nCrawl-delay: 10\n\nUser-agent: *\nDisallow:\n";
    }

    location /static/ {
        alias /home/chris/www/garberbucks.com/staticfiles/;
    }

    location / {
        # Answer the missing trailing slash here instead of a gunicorn round
        # trip for APPEND_SLASH, as soccerstats.us does.
        rewrite ^([^.]*[^/])$ $1/ permanent;

        # Zones are defined in s2's etc/nginx/conf.d/ai-bot-ratelimit.conf.
        limit_req zone=aibots burst=5 nodelay;
        limit_req zone=amazonbot burst=2 nodelay;
        limit_req zone=bytedance burst=2 nodelay;
        limit_req zone=petalbot burst=2 nodelay;
        limit_req zone=shapbot burst=2 nodelay;
        limit_req zone=metabot burst=2 nodelay;
        limit_req zone=seobot burst=2 nodelay;
        limit_req zone=perplexity burst=2 nodelay;
        limit_req zone=reflectionbot burst=2 nodelay;
        limit_req_status 429;
        proxy_pass http://127.0.0.1:8101;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    listen 80;
}
server {
    server_name www.garberbucks.com;
    return 301 https://garberbucks.com$request_uri;

    listen 80;
}
