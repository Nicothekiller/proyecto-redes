FROM nixos/nix:2.28.3
RUN echo "experimental-features = nix-command flakes" >> /etc/nix/nix.conf
COPY flake.nix flake.lock /src/
RUN mkdir /flake \
 && tr -d '\r' < /src/flake.nix > /flake/flake.nix \
 && tr -d '\r' < /src/flake.lock > /flake/flake.lock \
 && nix print-dev-env /flake | grep -v '^eval "${shellHook:-}"$' > /etc/devshell.sh
RUN printf '#!/root/.nix-profile/bin/bash\nsource /etc/devshell.sh\nexec "$@"\n' > /devshell \
 && chmod +x /devshell
WORKDIR /repo
ENTRYPOINT ["/devshell"]
