import psutil
import requests
import json
import logging
import click
import os
from datetime import datetime
import socket


class ServerMonitor:

    def __init__(self, webhook_url, threshold=90, server_name="Server"):
        self.webhook_url = webhook_url
        self.threshold = threshold
        self.server_name = server_name
        logging.basicConfig(
            level=logging.INFO,
            handlers=[
                logging.FileHandler(f"{os.path.basename(__file__)}.log", "a",
                                    "utf-8"),
            ],
            format="%(asctime)s %(levelname)s %(message)s",
            datefmt="%m-%d %H:%M:%S",
        )

    def check_server_status(self):
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        memory = psutil.virtual_memory()
        disk_usage = psutil.disk_usage('/')
        system_load = psutil.getloadavg()

        if (cpu_percent > self.threshold or memory.percent > self.threshold or
                disk_usage.percent > self.threshold or
                system_load[0] > self.threshold):
            return True
        else:
            return False

    def send_notification(self):
        disk_usage = psutil.disk_usage('/')
        memory = psutil.virtual_memory()
        cpu_count = psutil.cpu_count()
        system_load = psutil.getloadavg()
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        msg = f"{self.server_name} {current_time}\n\n"
        msg += f"**CPU利用率：** {psutil.cpu_percent(interval=1)}% ({cpu_count} cores)\n"
        msg += f"**内存使用：** {memory.percent}% (内存总大小：{self.bytes_to_gb(memory.total)}GB)\n"
        msg += f"**磁盘利用率：** {disk_usage.percent}% (剩余磁盘空间：{self.bytes_to_gb(disk_usage.free)}GB)\n"
        msg += f"**系统负载：** {system_load[0]:.2f}\n"

        is_exception = self.check_server_status()
        if is_exception or (datetime.now().hour == 10 and
                            datetime.now().minute < 3):
            logging.info("服务器运行%s: %s", '异常' if is_exception else '正常', msg)
            if is_exception:
                msg += f"<font color='warning'>**服务器运行异常, 请尽快处理!**</font>\n"
            else:
                msg += f"服务器运行正常\n"
            message = {"msgtype": "markdown", "markdown": {"content": msg}}

            response = requests.post(
                self.webhook_url,
                data=json.dumps(message),
                headers={'Content-Type': 'application/json'})

            if response.status_code == 200:
                logging.info("消息发送成功！")
            else:
                logging.error(f"消息发送失败: {response.status_code}")
        else:
            logging.info("服务器运行正常: %s", msg)

    @staticmethod
    def bytes_to_gb(bytes):
        gb = bytes / (1024**3)
        return round(gb, 2)


@click.command()
@click.option("--webhook_url", required=True, help="企业微信机器人的Webhook")
@click.option("--threshold", default=90, required=True, help="告警阈值")
@click.option("--server_name", default="Server", required=True, help="服务器名称")
def main(webhook_url, threshold, server_name):
    server_monitor = ServerMonitor(webhook_url, threshold, server_name)
    server_monitor.send_notification()


if __name__ == "__main__":
    main()