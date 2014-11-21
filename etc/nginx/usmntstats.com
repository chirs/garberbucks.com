

server {

            listen   80;
            server_name usmnt.edgemon.org;

            location / {
                        root   /home/chris/www/usmntstats.com/src/;
                        index  index.html;
                        }

}
