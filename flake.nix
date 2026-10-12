{
  description = "Minimal WireGuard coordination server devshell";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };
        python = pkgs.python313.withPackages (ps: with ps; [
          fastapi
          uvicorn
          requests
          pytest
        ]);
      in
      {
        devShells.default = pkgs.mkShell {
          name = "redes-overlay";

          packages = [
            python
            pkgs.wireguard-tools
            pkgs.iproute2
            pkgs.iputils
            pkgs.iperf3
            pkgs.curl
            pkgs.sqlite
            pkgs.tcpdump
            pkgs.netcat-gnu
          ];

          shellHook = ''
            echo "redes-overlay devshell"
            python3 --version
            wg --version
          '';
        };
      });
}
