import subprocess

def get_drive_io(
        drive_name: str,
) -> tuple[int, int]:
    """
    Block for wait_time seconds and returns the read / write stats happened during the block time

    :param drive_name: id of drive, can be obtained using lsblk
    :param wait_time: wait time of the function
    :return: a tuple with format [Byte read, Byte write]
    """

    pass

def get_all_drive_name() -> tuple[str]:
    """
    Returns a tuple with name of all physical drives currently mounted

    :return: a tuple of all physical drive names
    """

    pass

def get_drive_info(
        drive_name: str
) -> dict[str:str]:
    """
    Returns relevant hardware info of target drive

    :param drive_name: id of drive, can be obtained using lsblk
    :return: a dictionary with keys: model, serial, size, available_size
    """

    pass

def get_all_process_id_name() -> dict[int:str]:
    """
    Returns a dictionary containing all running process and relevant info

    :return: a dictionary with key of every PID and value of the process name

    """

    pass

def get_pid_info(
        pid:int
) -> dict[str:str]:
    """
    Returns relevant info of target process

    :param pid: PID of target process
    :return: a dictionary with keys: total_read, total_write, mem_occupied
    """

    pass

def get_pid_open_file(
        pid:int
) -> tuple[str]:
    """
    Returns a tuple of all files opened by process PID

    :param pid: PID of target process
    :return: a tuple of all opened file by the target process
    """

    pass

