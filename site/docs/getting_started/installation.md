# Installing Dooit & Dooit Extras

Dooit can be installed via various package managers

## PyPI

```bash
pip install dooit dooit-extras
```

## UV

```bash
uv tool install --with dooit-extras dooit
```

## Arch Linux

```bash
yay -S dooit dooit-extras
```

## NixOS

:::details Flakes/Module ❄️

```nix{24,7-8,}
# flake.nix

{
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";

    dooit.url = "github:dooit-org/dooit";
    dooit-extras.url = "github:dooit-org/dooit-extras";
  };
  # ...

  outputs = inputs @ {
    nixpkgs,
    ...
  }: let
    pkgs = import nixpkgs {};
    system = "x86_64-linux"; # change to whatever your system should be
  in {
    nixosConfigurations."${host}" = nixpkgs.lib.nixosSystem {
      specialArgs = {
        inherit system inputs pkgs;
      };
      modules = [
        ./dooit.nix
      ];
    };
  };
}
```

---

```nix
# dooit.nix

{
  inputs,
  pkgs,
  ...
}: let
  mydooit = pkgs.dooit.override {
    extraPackages = [
      pkgs.dooit-extras
    ];
  };
in {

  # this overlay allows you to use dooit from pkgs.dooit
  nixpkgs.overlays = [inputs.dooit.overlay inputs.dooit-extras.overlay];

  environment.systemPackages = [
    mydooit
  ];
}
```

:::

:::details Flakes/Home Manager ❄️

```nix{26,7-8,}
# flake.nix

{
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";

    dooit.url = "github:dooit-org/dooit";
    dooit-extras.url = "github:dooit-org/dooit-extras";
  };
  # ...

  outputs = inputs @ {
    nixpkgs,
    ...
  }: let
    pkgs = import nixpkgs {};
    system = "x86_64-linux"; # change to whatever your system should be
  in {
    homeConfigurations."${username}" = nixpkgs.lib.nixosSystem {
      pkgs = pkgs;
      extraSpecialArgs = {
        inherit system inputs;
      };

      modules = [
        ./home-manager/dooit.nix
      ];
    };
  };
}
```

---

```nix
# home-manager/dooit.nix

{
  inputs,
  pkgs,
  ...
}: {
  imports = [
    # home manager module for dooit
    inputs.dooit.homeManagerModules.default
  ];

  # adds dooit-extras to pkgs
  nixpkgs.overlays = [inputs.dooit-extras.overlay];

  programs.dooit = {
    enable = true;
    extraPackages = [pkgs.dooit-extras];
  };
}

```

:::

> Thanks to [`Hyprpanel`](https://hyprpanel.com/) from whom I stole the format for the flake

## Conda

```bash
conda install dooit dooit-extras
```

```bash
mamba install dooit dooit-extras
```

Or using [Pixi](https://pixi.sh/latest/)s `global` feature for access independent of the directory:

```bash
pixi global install dooit
```
