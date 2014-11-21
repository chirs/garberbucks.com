

server {

            listen   80;
            server_name usmnt.soccerstats.us;

            location / {
                        root   /home/chris/www/usmntstats/src/;
                        index  index.html;
                        }

}
