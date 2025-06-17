#!/usr/bin/env python3
"""
CLI Playground utility for simulating Linux commands in the GUI.
Provides a safe, educational terminal simulation environment.
"""

from datetime import datetime
from typing import Dict, List, Tuple, Any
import subprocess
import os
import json
import shlex
from pathlib import Path



class CLIPlayground:
    """Simulates a Linux command-line interface for educational purposes."""
    
    def __init__(self):
        """Initialize the CLI playground."""
        self.current_directory = "/home/user"
        self.username = "user"
        self.hostname = "linux-playground"
        self.command_history = []
        self.command_history = []
        self.current_directory = os.getcwd()
        self.safe_commands = {
            'ls': self._cmd_ls,
            'pwd': self._cmd_pwd,
            'cd': self._cmd_cd,
            'echo': self._cmd_echo,
            'cat': self._cmd_cat,
            'head': self._cmd_head,
            'tail': self._cmd_tail,
            'grep': self._cmd_grep,
            'find': self._cmd_find,
            'wc': self._cmd_wc,
            'sort': self._cmd_sort,
            'uniq': self._cmd_uniq,
            'date': self._cmd_date,
            'whoami': self._cmd_whoami,
            'ps': self._cmd_ps,
            'df': self._cmd_df,
            'free': self._cmd_free,
            'uptime': self._cmd_uptime,
            'history': self._cmd_history,
            'clear': self._cmd_clear,
            'help': self._cmd_help
        }
        
        # Create a safe sandbox directory
        self.sandbox_dir = Path.cwd() / "cli_sandbox"
        self.sandbox_dir.mkdir(exist_ok=True)
        
        # Initialize sample files
        self._create_sample_files()
        
        # Simulated file system
        self.file_system = {
            "/home/user": {
                "app.py": {"type": "file", "size": 4096, "permissions": "-rwxr-xr-x"},
                "documents": {"type": "dir", "size": 4096, "permissions": "drwxr-xr--"},
                "notes.txt": {"type": "file", "size": 8192, "permissions": "-rw-r--r--"}
            },
            "/home/user/documents": {
                "study_notes.md": {"type": "file", "size": 2048, "permissions": "-rw-r--r--"},
                "configs": {"type": "dir", "size": 4096, "permissions": "drwxr-xr-x"}
            }
        }
    
    def get_prompt(self) -> str:
        """
        Get the current command prompt.
        
        Returns:
            str: Formatted prompt string
        """
        return f"{self.username}@{self.hostname}:~$ "
    
    def get_welcome_message(self) -> str:
        """
        Get the welcome message for the CLI playground.
        
        Returns:
            str: Welcome message
        """
        return (
            "Welcome to the Linux Command Playground!\n"
            "Type 'help' for a list of simulated commands.\n"
        )
    
    def process_command(self, command_str: str) -> str:
        """
        Process a command and return simulated output.
        
        Args:
            command_str (str): The command string to process
            
        Returns:
            str: Simulated command output
        """
        command_str = command_str.strip()
        if not command_str:
            return ""
        
        # Add to history
        self.command_history.append(command_str)
        
        # Parse command and arguments
        parts = command_str.split()
        command = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []
        
        # Dispatch to appropriate handler
        command_handlers = {
            "help": self._handle_help,
            "clear": self._handle_clear,
            "ls": self._handle_ls,
            "pwd": self._handle_pwd,
            "whoami": self._handle_whoami,
            "date": self._handle_date,
            "uname": self._handle_uname,
            "cat": self._handle_cat,
            "cd": self._handle_cd,
            "mkdir": self._handle_mkdir,
            "touch": self._handle_touch,
            "rm": self._handle_rm,
            "cp": self._handle_cp,
            "mv": self._handle_mv,
            "grep": self._handle_grep,
            "ps": self._handle_ps,
            "top": self._handle_top,
            "df": self._handle_df,
            "free": self._handle_free,
            "history": self._handle_history,
            # Linux+ specific commands
            "grub2-install": self._handle_grub2_install,
            "grub2-mkconfig": self._handle_grub2_mkconfig,
            "update-grub": self._handle_update_grub,
            "mkinitrd": self._handle_mkinitrd,
            "dracut": self._handle_dracut,
            "nmap": self._handle_nmap,
            "systemctl": self._handle_systemctl,
            "journalctl": self._handle_journalctl,
            "firewall-cmd": self._handle_firewall_cmd,
            "iptables": self._handle_iptables,
            "lsmod": self._handle_lsmod,
            "modprobe": self._handle_modprobe,
            "lsblk": self._handle_lsblk,
            "fdisk": self._handle_fdisk,
            "mount": self._handle_mount,
            "umount": self._handle_umount,
        }
        
        if command in command_handlers:
            return command_handlers[command](args)
        else:
            return f"-bash: {command}: command not found"
    
    def _handle_help(self, args: List[str]) -> str:
        """Handle the help command."""
        return (
            "Simulated Commands Available:\n\n"
            "Basic Commands:\n"
            "  help                    - Shows this help message\n"
            "  clear                   - Clears the terminal screen\n"
            "  ls [-l] [path]          - Lists files and directories\n"
            "  pwd                     - Shows current directory\n"
            "  cd [directory]          - Changes directory\n"
            "  cat [file]              - Displays file contents\n"
            "  mkdir [directory]       - Creates directory\n"
            "  touch [file]            - Creates empty file\n"
            "  rm [file]               - Removes file\n"
            "  cp [source] [dest]      - Copies file\n"
            "  mv [source] [dest]      - Moves/renames file\n"
            "  grep [pattern] [file]   - Searches for pattern\n"
            "  whoami                  - Shows current user\n"
            "  date                    - Shows current date\n"
            "  history                 - Shows command history\n\n"
            "System Information:\n"
            "  uname [-a]              - System information\n"
            "  ps [aux]                - Shows running processes\n"
            "  top                     - Shows system resource usage\n"
            "  df [-h]                 - Shows disk usage\n"
            "  free [-h]               - Shows memory usage\n\n"
            "Linux+ Specific Commands:\n"
            "  grub2-install [device]  - Installs GRUB2 bootloader\n"
            "  grub2-mkconfig [-o]     - Generates GRUB config\n"
            "  update-grub             - Updates GRUB (Debian-based)\n"
            "  mkinitrd [args]         - Creates initrd image\n"
            "  dracut [args]           - Creates initramfs image\n"
            "  nmap [options] [host]   - Network scanning\n"
            "  systemctl [action] [service] - Service management\n"
            "  journalctl [options]    - View system logs\n"
            "  firewall-cmd [options]  - Firewall management\n"
            "  iptables [options]      - Advanced firewall rules\n"
            "  lsmod                   - Lists loaded kernel modules\n"
            "  modprobe [module]       - Loads kernel module\n"
            "  lsblk                   - Lists block devices\n"
            "  fdisk [options]         - Disk partitioning\n"
            "  mount [device] [point]  - Mounts filesystem\n"
            "  umount [device]         - Unmounts filesystem"
        )
    
    def _handle_clear(self, args: List[str]) -> str:
        """Handle the clear command."""
        return "CLEAR_SCREEN"  # Special return value to indicate screen clear
    
    def _handle_ls(self, args: List[str]) -> str:
        """Handle the ls command."""
        long_format = "-l" in args
        path = self.current_directory
        
        # Find path argument if provided
        for arg in args:
            if not arg.startswith("-"):
                path = arg if arg.startswith("/") else f"{self.current_directory}/{arg}"
                break
        
        # Get directory contents
        if path in self.file_system:
            contents = self.file_system[path]
            
            if long_format:
                result = "total 24\n"
                for name, info in contents.items():
                    size = info.get("size", 4096)
                    perms = info.get("permissions", "-rw-r--r--")
                    result += f"{perms} 1 user user {size:>4} Jun  4 14:00 {name}\n"
                return result.rstrip()
            else:
                return "    ".join(contents.keys())
        else:
            return f"ls: cannot access '{path}': No such file or directory"
    
    def _handle_pwd(self, args: List[str]) -> str:
        """Handle the pwd command."""
        return self.current_directory
    
    def _handle_whoami(self, args: List[str]) -> str:
        """Handle the whoami command."""
        return self.username
    
    def _handle_date(self, args: List[str]) -> str:
        """Handle the date command."""
        return datetime.now().strftime("%a %b %d %H:%M:%S %Z %Y")
    
    def _handle_uname(self, args: List[str]) -> str:
        """Handle the uname command."""
        if "-a" in args:
            return "Linux linux-playground 5.15.0-58-generic #64-Ubuntu SMP Thu Jan 5 11:43:13 UTC 2023 x86_64 x86_64 x86_64 GNU/Linux"
        else:
            return "Linux"
    
    def _handle_cat(self, args: List[str]) -> str:
        """Handle the cat command."""
        if not args:
            return "cat: missing file operand"
        
        filename = args[0]
        if filename == "notes.txt":
            return "These are my Linux study notes.\nRemember to practice commands daily!"
        elif filename == "app.py":
            return "#!/usr/bin/env python3\nprint('Hello, Linux world!')"
        else:
            return f"cat: {filename}: No such file or directory"
    
    def _handle_cd(self, args: List[str]) -> str:
        """Handle the cd command."""
        if not args:
            self.current_directory = "/home/user"
            return ""
        
        target = args[0]
        if target == "..":
            if self.current_directory != "/":
                self.current_directory = "/".join(self.current_directory.split("/")[:-1]) or "/"
        elif target.startswith("/"):
            if target in self.file_system:
                self.current_directory = target
            else:
                return f"cd: {target}: No such file or directory"
        else:
            new_path = f"{self.current_directory}/{target}"
            if new_path in self.file_system:
                self.current_directory = new_path
            else:
                return f"cd: {target}: No such file or directory"
        
        return ""
    
    def _handle_mkdir(self, args: List[str]) -> str:
        """Handle the mkdir command."""
        if not args:
            return "mkdir: missing operand"
        
        dirname = args[0]
        return f"mkdir: created directory '{dirname}'"
    
    def _handle_touch(self, args: List[str]) -> str:
        """Handle the touch command."""
        if not args:
            return "touch: missing file operand"
        
        return ""  # touch command typically produces no output on success
    
    def _handle_rm(self, args: List[str]) -> str:
        """Handle the rm command."""
        if not args:
            return "rm: missing operand"
        
        return ""  # rm command typically produces no output on success
    
    def _handle_cp(self, args: List[str]) -> str:
        """Handle the cp command."""
        if len(args) < 2:
            return "cp: missing destination file operand"
        
        return ""  # cp command typically produces no output on success
    
    def _handle_mv(self, args: List[str]) -> str:
        """Handle the mv command."""
        if len(args) < 2:
            return "mv: missing destination file operand"
        
        return ""  # mv command typically produces no output on success
    
    def _handle_grep(self, args: List[str]) -> str:
        """Handle the grep command."""
        if len(args) < 2:
            return "grep: missing pattern or file"
        
        pattern = args[0]
        filename = args[1]
        
        if filename == "notes.txt":
            if "Linux" in pattern:
                return "These are my Linux study notes."
            else:
                return ""
        else:
            return f"grep: {filename}: No such file or directory"
    
    def _handle_ps(self, args: List[str]) -> str:
        """Handle the ps command."""
        if "aux" in args:
            return (
                "USER       PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND\n"
                "root         1  0.0  0.1 167432 11832 ?        Ss   10:30   0:01 /sbin/init\n"
                "root         2  0.0  0.0      0     0 ?        S    10:30   0:00 [kthreadd]\n"
                "user      1234  0.1  0.2  12345  5678 pts/0    Ss   10:31   0:00 -bash\n"
                "user      5678  0.0  0.1   9876  3456 pts/0    R+   14:25   0:00 ps aux"
            )
        else:
            return (
                "  PID TTY          TIME CMD\n"
                " 1234 pts/0    00:00:00 bash\n"
                " 5678 pts/0    00:00:00 ps"
            )
    
    def _handle_top(self, args: List[str]) -> str:
        """Handle the top command."""
        return (
            "top - 14:25:30 up  3:55,  1 user,  load average: 0.15, 0.10, 0.05\n"
            "Tasks: 142 total,   1 running, 141 sleeping,   0 stopped,   0 zombie\n"
            "%Cpu(s):  2.3 us,  1.0 sy,  0.0 ni, 96.7 id,  0.0 wa,  0.0 hi,  0.0 si,  0.0 st\n"
            "MiB Mem :   7943.6 total,   4125.2 free,   1876.3 used,   1942.1 buff/cache\n"
            "MiB Swap:   2048.0 total,   2048.0 free,      0.0 used.   5789.4 avail Mem\n\n"
            "  PID USER      PR  NI    VIRT    RES    SHR S  %CPU  %MEM     TIME+ COMMAND\n"
            " 1234 user      20   0   12345   5678   3456 S   1.0   0.1   0:00.50 python3\n"
            " 5678 user      20   0    9876   3456   2345 R   0.5   0.0   0:00.10 top"
        )
    
    def _handle_df(self, args: List[str]) -> str:
        """Handle the df command."""
        if "-h" in args:
            return (
                "Filesystem      Size  Used Avail Use% Mounted on\n"
                "/dev/sda1        20G   12G  7.2G  62% /\n"
                "/dev/sda2       100G   45G   50G  48% /home\n"
                "tmpfs           4.0G     0  4.0G   0% /dev/shm"
            )
        else:
            return (
                "Filesystem     1K-blocks     Used Available Use% Mounted on\n"
                "/dev/sda1       20971520 12582912   7340032  62% /\n"
                "/dev/sda2      104857600 47185920  52428800  48% /home\n"
                "tmpfs            4194304        0   4194304   0% /dev/shm"
            )
    
    def _handle_free(self, args: List[str]) -> str:
        """Handle the free command."""
        if "-h" in args:
            return (
                "              total        used        free      shared  buff/cache   available\n"
                "Mem:          7.8Gi       1.8Gi       4.0Gi       256Mi       1.9Gi       5.7Gi\n"
                "Swap:         2.0Gi          0B       2.0Gi"
            )
        else:
            return (
                "              total        used        free      shared  buff/cache   available\n"
                "Mem:        8134656     1876352     4125184      262144     1942016     5789440\n"
                "Swap:       2097152           0     2097152"
            )
    
    def _handle_history(self, args: List[str]) -> str:
        """Handle the history command."""
        result = ""
        for i, cmd in enumerate(self.command_history[-20:], 1):  # Show last 20 commands
            result += f"  {i:3d}  {cmd}\n"
        return result.rstrip()
    
    # Linux+ Specific Commands
    
    def _handle_grub2_install(self, args: List[str]) -> str:
        """Handle the grub2-install command."""
        if not args:
            return "grub2-install: error: missing device argument"
        
        device = args[0]
        return (
            f"Installing for i386-pc platform.\n"
            f"Installation finished. No error reported."
        )
    
    def _handle_grub2_mkconfig(self, args: List[str]) -> str:
        """Handle the grub2-mkconfig command."""
        return (
            "Generating grub configuration file ...\n"
            "Found background: /usr/share/images/desktop-base/desktop-grub.png\n"
            "Found linux image: /boot/vmlinuz-5.15.0-58-generic\n"
            "Found initrd image: /boot/initrd.img-5.15.0-58-generic\n"
            "Warning: os-prober will not be executed to detect other bootable partitions.\n"
            "Done"
        )
    
    def _handle_update_grub(self, args: List[str]) -> str:
        """Handle the update-grub command."""
        return (
            "Sourcing file `/etc/default/grub'\n"
            "Generating grub configuration file ...\n"
            "Found linux image: /boot/vmlinuz-5.15.0-58-generic\n"
            "Found initrd image: /boot/initrd.img-5.15.0-58-generic\n"
            "Done"
        )
    
    def _handle_mkinitrd(self, args: List[str]) -> str:
        """Handle the mkinitrd command."""
        return "Creating initrd image... Success."
    
    def _handle_dracut(self, args: List[str]) -> str:
        """Handle the dracut command."""
        return (
            "dracut: Executing: /usr/bin/dracut\n"
            "dracut: Creating image file done"
        )
    
    def _handle_nmap(self, args: List[str]) -> str:
        """Handle the nmap command."""
        if not args:
            return "Please specify a host to scan. Example: nmap target.com"
        
        host = args[-1]  # Last argument is typically the target
        return (
            f"Starting Nmap 7.92 ( https://nmap.org ) at {datetime.now().strftime('%Y-%m-%d %H:%M')} EST\n"
            f"Nmap scan report for {host}\n"
            "Host is up (0.021s latency).\n"
            "Not shown: 996 filtered ports\n"
            "PORT    STATE SERVICE  VERSION\n"
            "22/tcp  open  ssh      OpenSSH 8.2p1 Ubuntu 4ubuntu0.4\n"
            "80/tcp  open  http     Apache httpd 2.4.41\n"
            "443/tcp open  ssl/http Apache httpd 2.4.41\n"
            "3306/tcp open mysql    MySQL 8.0.28\n"
            "Service detection performed. Please report any incorrect results at https://nmap.org/submit/\n"
            f"Nmap done: 1 IP address (1 host up) scanned in 8.42 seconds"
        )
    
    def _handle_systemctl(self, args: List[str]) -> str:
        """Handle the systemctl command."""
        if not args:
            return "systemctl: missing action"
        
        action = args[0]
        service = args[1] if len(args) > 1 else ""
        
        if action == "status":
            if service:
                return f"● {service}.service - {service.title()} Service\n   Active: active (running) since Mon 2023-06-04 10:30:15 EST; 3h 55min ago"
            else:
                return "systemctl: missing service name"
        elif action == "start":
            return f"Started {service}.service" if service else "systemctl: missing service name"
        elif action == "stop":
            return f"Stopped {service}.service" if service else "systemctl: missing service name"
        elif action == "restart":
            return f"Restarted {service}.service" if service else "systemctl: missing service name"
        else:
            return f"systemctl: unknown action '{action}'"
    
    def _handle_journalctl(self, args: List[str]) -> str:
        """Handle the journalctl command."""
        return (
            "-- Logs begin at Mon 2023-06-04 10:30:15 EST, end at Mon 2023-06-04 14:25:30 EST. --\n"
            "Jun 04 10:30:15 linux-playground systemd[1]: Starting System Logging Service...\n"
            "Jun 04 10:30:15 linux-playground systemd[1]: Started System Logging Service.\n"
            "Jun 04 14:20:00 linux-playground sshd[1234]: Accepted publickey for user from 192.168.1.100\n"
            "Jun 04 14:25:30 linux-playground kernel: [12345.678901] CPU0: Temperature above threshold"
        )
    
    def _handle_firewall_cmd(self, args: List[str]) -> str:
        """Handle the firewall-cmd command."""
        if "--list-all" in args:
            return (
                "public (active)\n"
                "  target: default\n"
                "  icmp-block-inversion: no\n"
                "  interfaces: eth0\n"
                "  sources:\n"
                "  services: dhcpv6-client ssh\n"
                "  ports: 80/tcp 443/tcp\n"
                "  protocols:\n"
                "  masquerade: no\n"
                "  forward-ports:\n"
                "  source-ports:\n"
                "  icmp-blocks:\n"
                "  rich rules:"
            )
        else:
            return "success"
    
    def _handle_iptables(self, args: List[str]) -> str:
        """Handle the iptables command."""
        if "-L" in args:
            return (
                "Chain INPUT (policy ACCEPT)\n"
                "target     prot opt source               destination\n"
                "ACCEPT     all  --  anywhere             anywhere             ctstate RELATED,ESTABLISHED\n"
                "ACCEPT     all  --  anywhere             anywhere\n"
                "INPUT_direct  all  --  anywhere             anywhere\n\n"
                "Chain FORWARD (policy ACCEPT)\n"
                "target     prot opt source               destination\n"
                "FORWARD_direct  all  --  anywhere             anywhere\n\n"
                "Chain OUTPUT (policy ACCEPT)\n"
                "target     prot opt source               destination\n"
                "OUTPUT_direct  all  --  anywhere             anywhere"
            )
        else:
            return ""
    
    def _handle_lsmod(self, args: List[str]) -> str:
        """Handle the lsmod command."""
        return (
            "Module                  Size  Used by\n"
            "nvidia_drm             65536  2\n"
            "nvidia_modeset       1142784  1 nvidia_drm\n"
            "nvidia              34144256  2 nvidia_uvm,nvidia_modeset\n"
            "drm_kms_helper        208896  1 nvidia_drm\n"
            "drm                   491520  4 drm_kms_helper,nvidia_drm\n"
            "ext4                  737280  2\n"
            "mbcache                24576  1 ext4\n"
            "jbd2                  131072  1 ext4"
        )
    
    def _handle_modprobe(self, args: List[str]) -> str:
        """Handle the modprobe command."""
        if not args:
            return "modprobe: missing module name"
        
        module = args[0]
        return f"Module {module} loaded successfully" if module else "modprobe: missing module name"
    
    def _handle_lsblk(self, args: List[str]) -> str:
        """Handle the lsblk command."""
        return (
            "NAME   MAJ:MIN RM  SIZE RO TYPE MOUNTPOINT\n"
            "sda      8:0    0   120G  0 disk\n"
            "├─sda1   8:1    0    20G  0 part /\n"
            "├─sda2   8:2    0   100G  0 part /home\n"
            "└─sda3   8:3    0     2G  0 part [SWAP]\n"
            "sr0     11:0    1  1024M  0 rom"
        )
    
    def _handle_fdisk(self, args: List[str]) -> str:
        """Handle the fdisk command."""
        if "-l" in args:
            return (
                "Disk /dev/sda: 120 GiB, 128849018880 bytes, 251658240 sectors\n"
                "Disk model: EXAMPLE SSD\n"
                "Units: sectors of 1 * 512 = 512 bytes\n"
                "Sector size (logical/physical): 512 bytes / 512 bytes\n"
                "I/O size (minimum/optimal): 512 bytes / 512 bytes\n"
                "Disklabel type: gpt\n"
                "Disk identifier: 12345678-1234-5678-9ABC-DEF012345678\n\n"
                "Device     Start       End   Sectors  Size Type\n"
                "/dev/sda1   2048  41945087  41943040   20G Linux filesystem\n"
                "/dev/sda2 41945088 251658206 209713119  100G Linux filesystem\n"
                "/dev/sda3 251658207 251658239        33  2G Linux swap"
            )
        else:
            return "fdisk: missing device argument"
    
    def _handle_mount(self, args: List[str]) -> str:
        """Handle the mount command."""
        if not args:
            return (
                "/dev/sda1 on / type ext4 (rw,relatime)\n"
                "/dev/sda2 on /home type ext4 (rw,relatime)\n"
                "tmpfs on /dev/shm type tmpfs (rw,nosuid,nodev)\n"
                "proc on /proc type proc (rw,nosuid,nodev,noexec,relatime)"
            )
        elif len(args) >= 2:
            device, mountpoint = args[0], args[1]
            return f"Mounted {device} on {mountpoint}"
        else:
            return "mount: missing mountpoint"
    
    def _handle_umount(self, args: List[str]) -> str:
        """Handle the umount command."""
        if not args:
            return "umount: missing device or mountpoint"
        
        target = args[0]
        return f"Unmounted {target}"
    def _create_sample_files(self):
        """Create sample files for CLI practice"""
        sample_files = {
            'sample.txt': 'This is a sample text file.\nIt contains multiple lines.\nUse it to practice Linux commands!',
            'data.csv': 'name,age,city\nJohn,25,NYC\nJane,30,LA\nBob,35,Chicago',
            'notes.md': '# Linux Study Notes\n\n## Commands\n- ls: list files\n- cat: display file contents\n- grep: search text',
            'log.txt': 'INFO: Application started\nWARN: Low memory\nERROR: Connection failed\nINFO: Process completed'
        }
        
        for filename, content in sample_files.items():
            file_path = self.sandbox_dir / filename
            if not file_path.exists():
                file_path.write_text(content)
    
    def execute_command(self, command: str) -> Dict[str, Any]:
        """
        Execute a command safely in the CLI playground
        
        Args:
            command: The command string to execute
            
        Returns:
            Dict containing output, error, and status
        """
        if not command.strip():
            return {
                'output': '',
                'error': '',
                'status': 'success',
                'command': command
            }
        
        # Add to history
        self.command_history.append(command)
        
        # Parse command
        try:
            parts = shlex.split(command)
            cmd_name = parts[0].lower()
            args = parts[1:] if len(parts) > 1 else []
        except ValueError as e:
            return {
                'output': '',
                'error': f'Error parsing command: {e}',
                'status': 'error',
                'command': command
            }
        
        # Execute safe command
        if cmd_name in self.safe_commands:
            try:
                result = self.safe_commands[cmd_name](args)
                return {
                    'output': result,
                    'error': '',
                    'status': 'success',
                    'command': command
                }
            except Exception as e:
                return {
                    'output': '',
                    'error': f'Error executing {cmd_name}: {e}',
                    'status': 'error',
                    'command': command
                }
        else:
            return {
                'output': '',
                'error': f'Command "{cmd_name}" not allowed in playground. Type "help" for available commands.',
                'status': 'error',
                'command': command
            }
    
    def _cmd_ls(self, args: List[str]) -> str:
        """List directory contents"""
        target_dir = self.sandbox_dir
        
        if args and args[0] != '-l':
            # Simple path handling for safety
            if args[0] == '..':
                return 'Permission denied: Cannot access parent directory'
            elif args[0] == '.':
                target_dir = self.sandbox_dir
        
        try:
            files = list(target_dir.iterdir())
            if '-l' in args:
                # Long format
                output = []
                for file in files:
                    stat = file.stat()
                    size = stat.st_size
                    name = file.name
                    file_type = 'd' if file.is_dir() else '-'
                    output.append(f'{file_type}rw-r--r-- 1 user user {size:8d} {name}')
                return '\n'.join(output)
            else:
                # Simple format
                return '  '.join([f.name for f in files if not f.name.startswith('.')])
        except Exception as e:
            return f'ls: {e}'
    
    def _cmd_pwd(self, args: List[str]) -> str:
        """Print working directory"""
        return str(self.sandbox_dir)
    
    def _cmd_cd(self, args: List[str]) -> str:
        """Change directory (limited to sandbox)"""
        if not args:
            return str(self.sandbox_dir)
        
        target = args[0]
        if target in ['..', '/', '~']:
            return 'Permission denied: Cannot leave sandbox directory'
        
        return f'Changed to {self.sandbox_dir}'
    
    def _cmd_echo(self, args: List[str]) -> str:
        """Echo arguments"""
        return ' '.join(args)
    
    def _cmd_cat(self, args: List[str]) -> str:
        """Display file contents"""
        if not args:
            return 'cat: missing filename'
        
        filename = args[0]
        file_path = self.sandbox_dir / filename
        
        if not file_path.exists():
            return f'cat: {filename}: No such file or directory'
        
        if not file_path.is_file():
            return f'cat: {filename}: Is a directory'
        
        try:
            return file_path.read_text()
        except Exception as e:
            return f'cat: {filename}: {e}'
    
    def _cmd_head(self, args: List[str]) -> str:
        """Display first lines of file"""
        if not args:
            return 'head: missing filename'
        
        filename = args[0]
        lines = 10  # default
        
        if len(args) > 1 and args[0] == '-n':
            try:
                lines = int(args[1])
                filename = args[2] if len(args) > 2 else None
            except (ValueError, IndexError):
                return 'head: invalid number of lines'
        
        if not filename:
            return 'head: missing filename'
        
        file_path = self.sandbox_dir / filename
        
        if not file_path.exists():
            return f'head: {filename}: No such file or directory'
        
        try:
            content = file_path.read_text()
            return '\n'.join(content.split('\n')[:lines])
        except Exception as e:
            return f'head: {filename}: {e}'
    
    def _cmd_tail(self, args: List[str]) -> str:
        """Display last lines of file"""
        if not args:
            return 'tail: missing filename'
        
        filename = args[0]
        lines = 10  # default
        
        if len(args) > 1 and args[0] == '-n':
            try:
                lines = int(args[1])
                filename = args[2] if len(args) > 2 else None
            except (ValueError, IndexError):
                return 'tail: invalid number of lines'
        
        if not filename:
            return 'tail: missing filename'
        
        file_path = self.sandbox_dir / filename
        
        if not file_path.exists():
            return f'tail: {filename}: No such file or directory'
        
        try:
            content = file_path.read_text()
            return '\n'.join(content.split('\n')[-lines:])
        except Exception as e:
            return f'tail: {filename}: {e}'
    
    def _cmd_grep(self, args: List[str]) -> str:
        """Search for pattern in file"""
        if len(args) < 2:
            return 'grep: missing pattern or filename'
        
        pattern = args[0]
        filename = args[1]
        file_path = self.sandbox_dir / filename
        
        if not file_path.exists():
            return f'grep: {filename}: No such file or directory'
        
        try:
            content = file_path.read_text()
            matching_lines = []
            for line in content.split('\n'):
                if pattern.lower() in line.lower():
                    matching_lines.append(line)
            return '\n'.join(matching_lines) if matching_lines else ''
        except Exception as e:
            return f'grep: {filename}: {e}'
    
    def _cmd_find(self, args: List[str]) -> str:
        """Find files"""
        if not args:
            files = list(self.sandbox_dir.iterdir())
            return '\n'.join([f'./{f.name}' for f in files if f.is_file()])
        
        if args[0] == '-name' and len(args) > 1:
            pattern = args[1].strip('"\'')
            files = list(self.sandbox_dir.glob(pattern))
            return '\n'.join([f'./{f.name}' for f in files])
        
        return 'find: simple usage only - try "find" or "find -name pattern"'
    
    def _cmd_wc(self, args: List[str]) -> str:
        """Word count"""
        if not args:
            return 'wc: missing filename'
        
        filename = args[0]
        file_path = self.sandbox_dir / filename
        
        if not file_path.exists():
            return f'wc: {filename}: No such file or directory'
        
        try:
            content = file_path.read_text()
            lines = len(content.split('\n'))
            words = len(content.split())
            chars = len(content)
            return f'{lines:8d} {words:8d} {chars:8d} {filename}'
        except Exception as e:
            return f'wc: {filename}: {e}'
    
    def _cmd_sort(self, args: List[str]) -> str:
        """Sort file contents"""
        if not args:
            return 'sort: missing filename'
        
        filename = args[0]
        file_path = self.sandbox_dir / filename
        
        if not file_path.exists():
            return f'sort: {filename}: No such file or directory'
        
        try:
            content = file_path.read_text()
            lines = content.split('\n')
            sorted_lines = sorted(lines)
            return '\n'.join(sorted_lines)
        except Exception as e:
            return f'sort: {filename}: {e}'
    
    def _cmd_uniq(self, args: List[str]) -> str:
        """Remove duplicate lines"""
        if not args:
            return 'uniq: missing filename'
        
        filename = args[0]
        file_path = self.sandbox_dir / filename
        
        if not file_path.exists():
            return f'uniq: {filename}: No such file or directory'
        
        try:
            content = file_path.read_text()
            lines = content.split('\n')
            unique_lines = []
            prev_line = None
            for line in lines:
                if line != prev_line:
                    unique_lines.append(line)
                prev_line = line
            return '\n'.join(unique_lines)
        except Exception as e:
            return f'uniq: {filename}: {e}'
    
    def _cmd_date(self, args: List[str]) -> str:
        """Display current date"""
        from datetime import datetime
        return datetime.now().strftime('%a %b %d %H:%M:%S %Z %Y')
    
    def _cmd_whoami(self, args: List[str]) -> str:
        """Display current user"""
        return 'student'
    
    def _cmd_ps(self, args: List[str]) -> str:
        """Display processes (simulated)"""
        return '''  PID TTY          TIME CMD
 1234 pts/0    00:00:01 bash
 5678 pts/0    00:00:00 python
 9012 pts/0    00:00:00 ps'''
    
    def _cmd_df(self, args: List[str]) -> str:
        """Display filesystem usage (simulated)"""
        return '''Filesystem     1K-blocks    Used Available Use% Mounted on
/dev/sda1       20480000 8192000  11264000  42% /
tmpfs            2048000  102400   1945600   5% /dev/shm'''
    
    def _cmd_free(self, args: List[str]) -> str:
        """Display memory usage (simulated)"""
        return 
    '''              total        used        free      shared  buff/cache   available
Mem:        8192000     2048000     4096000      102400     2048000     5632000
Swap:       2048000           0     2048000
'''
    
    def _cmd_uptime(self, args: List[str]) -> str:
        """Display system uptime (simulated)"""
        return ' 15:30:42 up 2 days,  4:30,  1 user,  load average: 0.15, 0.10, 0.05'
    
    def _cmd_history(self, args: List[str]) -> str:
        """Display command history"""
        if not self.command_history:
            return ''
        
        output = []
        for i, cmd in enumerate(self.command_history[-20:], 1):  # Last 20 commands
            output.append(f'{i:5d}  {cmd}')
        return '\n'.join(output)
    
    def _cmd_clear(self, args: List[str]) -> str:
        """Clear screen command"""
        return 'CLEAR_SCREEN'  # Special marker for frontend
    
    def _cmd_help(self, args: List[str]) -> str:
        """Display available commands"""
        return '''Linux Plus CLI Playground - Available Commands

    ═══════════════════════════════════════════════════════════

    FILE OPERATIONS:
    ls                    List files and directories
    cat <file>           Display file contents  
    head <file>          Show first 10 lines of file
    tail <file>          Show last 10 lines of file

    TEXT PROCESSING:
    grep <pattern> <file> Search for pattern in file
    wc <file>            Count lines, words, and characters
    sort <file>          Sort lines in file
    uniq <file>          Remove duplicate lines

    SYSTEM INFO:
    pwd                  Show current directory path
    whoami              Display current username
    date                Show current date and time
    ps                  Display running processes
    df                  Show filesystem usage
    free                Show memory usage
    uptime              Show system uptime

    UTILITIES:
    echo "text"         Display text
    find <path>         Find files and directories
    history             Show command history
    clear               Clear the terminal screen
    help                Show this help message

    ═══════════════════════════════════════════════════════════

    SAMPLE FILES: sample.txt, data.csv, notes.md, log.txt

    EXAMPLES:
    ls                  → List available files
    cat sample.txt      → View sample file contents
    grep INFO log.txt   → Search for "INFO" in log file
    wc data.csv         → Count lines/words/chars in CSV
    head -n 5 notes.md  → Show first 5 lines of notes

    Educational Linux environment for safe command practice.
    Note: This is a sandbox environment with limited functionality.
    '''

def get_cli_playground():
    """Get CLI playground instance"""
    return CLIPlayground()