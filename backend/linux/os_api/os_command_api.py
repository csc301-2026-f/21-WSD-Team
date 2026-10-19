import subprocess

def get_drive_io(
        drive_name: str,
        wait_time: int,
) -> tuple[int, int]:
    """
    Block for wait_time seconds and returns the read / write stats happened during the block time

    :param drive_name: id of drive, can be obtained using lsblk
    :param wait_time: wait time of the function
    :return: a tuple with format [Byte read, Byte write]

    example return: [1024, 1024]
    """

    pass

def get_all_drive_name() -> tuple[str]:
    """
    Returns a tuple with name of all physical drives currently mounted

    :return: a tuple of all physical drive names

    example return: (nvme0n1, nvme1n1, sda, sdb)
    """

    pass

def get_drive_info(
        drive_name: str
) -> dict[str:str]:
    """
    Returns relevant hardware info of target drive

    :param drive_name: id of drive, can be obtained using lsblk
    :return: a dictionary with keys: model, serial, size, available_size
    Size will always be in G

    example return: {model: "SN850X", serial: "xxxxxxxx", size: "931G", available_size: "341G"}

    """

    pass

def get_all_process_id_name() -> dict[int:str]:
    """
    Returns a dictionary containing all running process and relevant info

    :return: a dictionary with key of every PID and value of the process name

    example return: {114: "program1", 115: "program2", 325: "program3"}
    """

    pass

def get_pid_info(
        pid:int
) -> dict[str:str]:
    """
    Returns relevant info of target process

    :param pid: PID of target process
    :return: a dictionary with keys: total_read, total_write, mem_occupied
    mem_occupied will always be in unit KiB

    example return: {total_read: 114514, total_write: 325799, mem_occupied: 524288}
    """

    pass

def get_pid_open_file(
        pid:int
) -> tuple[str]:
    """
    Returns a tuple of all files opened by process PID

    :param pid: PID of target process
    :return: a tuple of all opened file by the target process

    example return: ("/home/xxx/program1", "/home/xxx/program2", "/mnt/smbshare/file1")
    """


    pass

