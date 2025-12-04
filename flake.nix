{
  description = "Example Python flake";

  inputs = {
    nixpkgs.url = "nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs }: let
    system = "x86_64-linux";
    pkgs = import nixpkgs { inherit system; };
  in {
    devShell.${system} = pkgs.mkShell {
      buildInputs = [
        (pkgs.python312.withPackages (python-pkgs: [
          # User libraries
          python-pkgs.numpy
          python-pkgs.pydantic
          python-pkgs.josepy
          python-pkgs.passlib
          python-pkgs.starlette
          python-pkgs.uvicorn
          python-pkgs.aiofiles
          python-pkgs.sqlalchemy

          # Extra tools
          python-pkgs.mypy
          python-pkgs.setuptools
        ]))

        pkgs.pyright
      ];
    };
  };
}
