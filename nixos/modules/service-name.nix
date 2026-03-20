# NixOS module template for service-template based services
# {{SERVICE_NAME}} を実際のサービス名に置き換える（camelCase で）
{ lib, config, pkgs, ... }:
let
  cfg = config.k12.serviceName;
  podman = "${pkgs.podman}/bin/podman";
in {
  options.k12.serviceName = {
    enable = lib.mkEnableOption "{{SERVICE_NAME}} pipeline";
    schedule = lib.mkOption {
      type    = lib.types.str;
      default = "*-*-* 06:00:00 UTC";
      description = "OnCalendar value for the systemd timer";
    };
  };

  config = lib.mkIf cfg.enable {
    systemd.tmpfiles.rules = [
      "d /srv/{{SERVICE_NAME}}           0755 kento users -"
      "d /srv/{{SERVICE_NAME}}/data      0755 kento users -"
      "d /srv/{{SERVICE_NAME}}/data/logs 0755 kento users -"
      "d /srv/{{SERVICE_NAME}}/auth      0700 kento users -"
    ];

    systemd.services.serviceName = {
      description = "{{SERVICE_NAME}} pipeline";
      serviceConfig = {
        Type = "oneshot";
        User = "kento";
        StandardOutput = "append:/srv/{{SERVICE_NAME}}/data/logs/systemd.log";
        StandardError  = "append:/srv/{{SERVICE_NAME}}/data/logs/systemd.log";
        ExecStart = lib.concatStringsSep " " [
          "${podman} run --rm"
          # ホスト側 loopback サービス（claude-gateway 等 127.0.0.1 にバインド）へ
          # アクセスする場合は --network=host を追加する。
          # "--network=host"
          "--env-file /srv/{{SERVICE_NAME}}/auth/.env"
          "-v /srv/{{SERVICE_NAME}}/data:/data:z"
          "-v /srv/{{SERVICE_NAME}}/auth:/auth:z"
          "k12-{{SERVICE_NAME}}:local"
        ];
        TimeoutStartSec = "3600";
      };
    };

    systemd.timers.serviceName = {
      description = "{{SERVICE_NAME}} timer";
      wantedBy    = [ "timers.target" ];
      timerConfig = {
        OnCalendar = cfg.schedule;
        Persistent = true;
      };
    };
  };
}
