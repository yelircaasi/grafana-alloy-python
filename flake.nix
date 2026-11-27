{
  description = "";
  inputs = {
    nixpkgs = {
      url = "github:nixos/nixpkgs/c57a028c30068aa2a7e00fa87300804dab748ff5";  # updated 2026-10-27
    };

    flake-utils = {
      url = "github:numtide/flake-utils/b7a79d3fea1e214f6d668d521cecec0c01e26544";  # updated 2026-10-27
    };
  };
  outputs = {
    self,
    nixpkgs,
    flake-utils,
  }:
    flake-utils.lib.eachDefaultSystem (system: let
      pkgs = nixpkgs.legacyPackages.${system};
    in {
      devShells.default =
        (pkgs.buildFHSEnv {
          name = "python-uv-env";
          targetPkgs = pkgs:
            with pkgs; [
              # julia
              pkgs.python314
              uv

              # Common build dependencies for Python packages
              gcc
              glibc
              zlib
              libffi
              openssl
              libxml2
              libxslt

              # Useful tools
              git
              curl
              pandoc
            ];
          runScript = "bash";
        }).env;
    });
}
