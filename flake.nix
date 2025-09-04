{
  description = "Flake for Dooit with default.nix integration";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
  };

  outputs =
    {
      self,
      nixpkgs,
      ...
    }:
    let
      forEachSystem = nixpkgs.lib.genAttrs nixpkgs.lib.platforms.all;

      pkgsFor = forEachSystem (
        system:
        import nixpkgs {
          inherit system;
        }
      );

      packageFor = system: pkgsFor.${system}.callPackage ./nix { };
    in
    {
      packages = forEachSystem (system: {
        default = packageFor system;
      });
      overlay = final: prev: {
        dooit = packageFor final.system;
      };

      homeManagerModules = {
        default = self.homeManagerModules.dooit;
        dooit = import ./nix/hm-module.nix self;
      };

      devShells = forEachSystem (
        system:
        let
          pkgs = pkgsFor.${system};
        in
        {
          default = pkgs.mkShell {
            buildInputs = with pkgs; [
              nodejs
              nodePackages.yarn
              nodePackages.npm
            ];
          };
        }
      );
    };
}
