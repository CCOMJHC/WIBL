#!/bin/bash -ev

sudo dnf install -y golang amazon-cloudwatch-agent sqlite sqlite-doc

sudo mkdir -p /usr/local/wibl/upload-server/bin \
    /usr/local/wibl/upload-server/etc/certs \
    /usr/local/wibl/upload-server/db \
    /usr/local/wibl/upload-server/log

# Add user and change permissions
sudo adduser wibl
sudo chown -R wibl:wibl /usr/local/wibl
sudo -u wibl chmod 0400 /usr/local/wibl/upload-server/etc/certs/server.key \
  /usr/local/wibl/upload-server/etc/certs/server.key
sudo -u wibl chmod 0400 /usr/local/wibl/upload-server/etc/certs/server.crt \
  /usr/local/wibl/upload-server/etc/certs/ca.crt
sudo -u wibl chmod 0500 /usr/local/wibl/upload-server/bin/*


# Allow upload server to bind to ports <1024 as non-root user (i.e., wibl)
sudo setcap 'CAP_NET_BIND_SERVICE=+ep' /usr/local/wibl/upload-server/bin/upload-server

# Setup systemd service
cat > /tmp/wibl-upload-server.service <<-HERE
[Unit]
Description=WIBL upload-server
After=network.target

[Service]
Type=exec
User=wibl
Group=wibl
CapabilityBoundingSet=CAP_NET_BIND_SERVICE
ExecStart=/usr/local/wibl/upload-server/bin/upload-server -config /usr/local/wibl/upload-server/etc/config.json
Restart=always

[Install]
WantedBy=multi-user.target
HERE
sudo mv /tmp/wibl-upload-server.service /etc/systemd/system/wibl-upload-server.service
sudo chown root:root /etc/systemd/system/wibl-upload-server.service

sudo systemctl daemon-reload
sudo systemctl enable wibl-upload-server
sudo systemctl start wibl-upload-server

# Setup CloudWatch agent
cat > /tmp/cloudwatch-agent.json <<-HERE
{
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/opt/aws/amazon-cloudwatch-agent/logs/amazon-cloudwatch-agent.log",
            "log_group_name": "wibl-upload-server",
            "log_stream_name": "amazon-cloudwatch-agent.log",
            "timezone": "UTC",
            "auto_removal": false,
            "retention_in_days": 60
          },
          {
            "file_path": "/usr/local/wibl/upload-server/log/console-*.log",
            "log_group_name": "wibl-upload-server",
            "log_stream_name": "console.log",
            "timezone": "UTC",
            "auto_removal": false,
            "retention_in_days": 60
          },
          {
            "file_path": "/usr/local/wibl/upload-server/log/access-*.log",
            "log_group_name": "wibl-upload-server",
            "log_stream_name": "access.log",
            "timezone": "UTC",
            "auto_removal": false,
            "retention_in_days": 60
          }
        ]
      }
    }
  }
}
HERE
sudo mv /tmp/cloudwatch-agent.json /opt/aws/amazon-cloudwatch-agent/etc/cloudwatch-agent.json
sudo chown root:root /opt/aws/amazon-cloudwatch-agent/etc/cloudwatch-agent.json
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
  -a fetch-config -m ec2 -s -c file:/opt/aws/amazon-cloudwatch-agent/etc/cloudwatch-agent.json
