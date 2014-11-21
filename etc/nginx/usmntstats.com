

server {
            listen   80;
            server_name  www.usmntstats.com;
            rewrite ^/(.*) http://usmntstats.com/$1 permanent;
           }


server {

            listen   80;
            server_name usmntstats.com

            location / {
                        root   /home/chris/www/usmntstats.com/src/;
                        index  index.html;
                        }

}
