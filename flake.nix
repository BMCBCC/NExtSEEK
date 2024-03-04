{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs, ... }:
    let pkgs = nixpkgs.legacyPackages.x86_64-linux;
    in {
      devShells."x86_64-linux".default = pkgs.mkShell {
        buildInputs = with pkgs; [
          python3
        ];
        propagatedBuildInputs = with pkgs.python3Packages; [
          beautifulsoup4
          bleach
          bunch
          certifi
          chardet
          deepmerge
          django
          django-contrib-comments
          django-crontab
          #django-realtime
          #django-rest-framework
          django-widget-tweaks
          djangorestframework
          et-xmlfile
          filebrowser_safe
          fpdf
          future
          grappelli-safe
          h5py
          html5lib
          idna
          #immpload
          inflection
          isodate
          jdcal
          joblib
          lxml
          markdown
          mezzanine
          mysqlclient
          numpy
          oauthlib
          olefile
          openpyxl
          pandas
          parse
          universal-pathlib
          pillow
          pymysql
          pyparsing
          python-dateutil
          python-docx
          pytz
          pyyaml
          rdflib
          reportlab
          requests
          requests-oauthlib
          simplejson
          six
          sparqlwrapper
          tzlocal
          unidecode
          urllib3
          webencodings
          xlwt
        ];
      };
    };
}
