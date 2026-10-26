Optional - exact Odoo 16 font (Oswald)
======================================
Install Oswald as a SYSTEM font on the server (wkhtmltopdf then uses it everywhere,
including header and footer):

    mkdir -p /usr/local/share/fonts/oswald
    cp Oswald-Regular.ttf Oswald-Bold.ttf /usr/local/share/fonts/oswald/
    fc-cache -f -v

(Download "Oswald" from https://fonts.google.com/specimen/Oswald - static/ folder.)
Restart Odoo afterwards. Without it the reports fall back to a DejaVu / Liberation font.
