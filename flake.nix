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
          python-pkgs.email-validator
          python-pkgs.python-jose
          python-pkgs.passlib
          python-pkgs.argon2-cffi
          python-pkgs.starlette
          python-pkgs.websockets
          python-pkgs.uvicorn
          python-pkgs.aiofiles
          python-pkgs.sqlalchemy
          python-pkgs.openai

          python-pkgs.ruff
        ]))

        pkgs.pyright
        pkgs.nodePackages.nodejs
      ];
    };
  };
}
