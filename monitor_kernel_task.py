#!/usr/bin/env python3

import csv
import datetime
import re
import subprocess
import time


LOG_FILE = "mac_thermal_monitor.csv"
SAMPLE_INTERVAL = 10


def run_cmd(cmd):
    try:
        return subprocess.check_output(
            cmd,
            shell=True,
            stderr=subprocess.DEVNULL,
            text=True
        )
    except Exception:
        return ""


def get_powermetrics():
    output = run_cmd(
        "sudo powermetrics --samplers smc -n 1"
    )

    data = {
        "cpu_temp": "",
        "gpu_temp": "",
        "fan_rpm": ""
    }

    cpu_match = re.search(
        r"CPU die temperature:\s+([\d.]+)",
        output
    )

    gpu_match = re.search(
        r"GPU die temperature:\s+([\d.]+)",
        output
    )

    fan_match = re.search(
        r"Fan:\s+(\d+)",
        output
    )

    if cpu_match:
        data["cpu_temp"] = cpu_match.group(1)

    if gpu_match:
        data["gpu_temp"] = gpu_match.group(1)

    if fan_match:
        data["fan_rpm"] = fan_match.group(1)

    return data


def get_kernel_task_cpu():
    output = run_cmd(
        "top -l 2 -stats pid,command,cpu"
    )

    matches = re.findall(
        r"^\s*\d+\s+kernel_task\s+([\d.]+)\s*$",
        output,
        re.MULTILINE
    )

    if matches:
        return float(matches[-1])

    output = run_cmd(
        "ps -axo pid,%cpu,comm"
    )

    match = re.search(
        r"^\s*\d+\s+([\d.]+)\s+.*/kernel_task$",
        output,
        re.MULTILINE
    )

    if match:
        return float(match.group(1))

    return 0.0


def get_total_cpu():
    output = run_cmd(
        "top -l 1 | grep 'CPU usage'"
    )

    match = re.search(
        r"(\d+\.\d+)% user,\s+(\d+\.\d+)% sys",
        output
    )

    if match:
        return float(match.group(1)) + float(match.group(2))

    return 0.0


def get_display_count():
    output = run_cmd(
        "system_profiler SPDisplaysDataType"
    )

    return output.count("Resolution:")


def get_external_disk_count():
    output = run_cmd(
        "diskutil list external"
    )

    return output.count("/dev/disk")


def get_gpu_mode():
    output = run_cmd(
        "system_profiler SPDisplaysDataType"
    )

    if "AMD Radeon" in output:
        return "Discrete"

    return "Unknown"


def evaluate_status(pm, kernel_task_cpu, total_cpu):
    cpu_temp = float(pm["cpu_temp"]) if pm["cpu_temp"] else 0.0
    gpu_temp = float(pm["gpu_temp"]) if pm["gpu_temp"] else 0.0

    if kernel_task_cpu >= 200 or cpu_temp >= 95 or gpu_temp >= 90:
        return "critical: kernel_task或温度异常偏高"

    if kernel_task_cpu >= 120 or cpu_temp >= 85 or gpu_temp >= 80:
        return "warning: 存在明显热节流或高负载风险"

    if kernel_task_cpu >= 60 or total_cpu >= 70:
        return "notice: 有一定负载，建议继续观察"

    return "ok: 运行平稳"


def init_csv():
    with open(LOG_FILE, "w", newline="") as f:
        writer = csv.writer(f)

        writer.writerow([
            "time",
            "cpu_temp",
            "gpu_temp",
            "fan_rpm",
            "kernel_task_cpu",
            "total_cpu",
            "display_count",
            "external_disks",
            "gpu_mode",
            "evaluation"
        ])


def write_record():
    pm = get_powermetrics()
    kernel_task_cpu = get_kernel_task_cpu()
    total_cpu = get_total_cpu()
    display_count = get_display_count()
    external_disk_count = get_external_disk_count()
    gpu_mode = get_gpu_mode()
    evaluation = evaluate_status(
        pm,
        kernel_task_cpu,
        total_cpu
    )

    row = [
        datetime.datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        ),
        pm["cpu_temp"],
        pm["gpu_temp"],
        pm["fan_rpm"],
        kernel_task_cpu,
        total_cpu,
        display_count,
        external_disk_count,
        gpu_mode,
        evaluation
    ]

    with open(LOG_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(row)

    print(
        f"[{row[0]}] CPU {row[1]}C | GPU {row[2]}C | "
        f"Fan {row[3]}rpm | kernel_task {kernel_task_cpu:.1f}% | "
        f"Total CPU {total_cpu:.1f}% | Eval {evaluation}"
    )


def main():
    init_csv()

    while True:
        write_record()
        time.sleep(SAMPLE_INTERVAL)


if __name__ == "__main__":
    main()