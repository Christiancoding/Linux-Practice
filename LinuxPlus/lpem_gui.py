# lpem_gui.py
import customtkinter as ctk
import threading
import queue
import time
import json
from pathlib import Path
from tkinter import filedialog # Used for selecting files/directories

# --- Placeholder for your refactored backend ---
# You will replace these placeholder calls with your actual backend logic.
# Your backend functions need to accept parameters and a log_queue.
class BackendPlaceholder:
    def list_vms(self, log_queue, libvirt_uri):
        log_queue.put("LOG: Requesting VM list...")
        # Simulate network delay
        time.sleep(1.5)
        # Simulate finding VMs
        vms = ["ubuntu24.04-1", "fedora-dev", "kali-rolling", "debian-stable"]
        log_queue.put(f"VMS_UPDATE:{','.join(vms)}") # Use a prefix for specific updates
        log_queue.put("LOG: VM list updated.")

    def list_challenges(self, log_queue, challenges_dir):
        log_queue.put(f"LOG: Requesting challenges from '{challenges_dir}'...")
        time.sleep(1)
        # Simulate finding challenges
        challenges = ["set_hostname", "manage_users_add", "create_tmp_file", "dns-lookup"]
        log_queue.put(f"CHALLENGES_UPDATE:{','.join(challenges)}")
        log_queue.put("LOG: Challenge list updated.")

    def setup_user(self, log_queue, vm_name, new_user, admin_user, admin_key, pub_key, libvirt_uri):
         log_queue.put(f"LOG: Starting user setup for '{new_user}' on '{vm_name}'...")
         log_queue.put(f"LOG:  > Using admin '{admin_user}' and key '{admin_key}'")
         log_queue.put(f"LOG:  > Installing public key '{pub_key}'")
         time.sleep(0.5)
         log_queue.put("PROGRESS: Connecting to libvirt...")
         time.sleep(1)
         log_queue.put("PROGRESS: Finding VM...")
         time.sleep(1)
         log_queue.put("PROGRESS: Starting VM if needed...")
         time.sleep(2)
         log_queue.put("PROGRESS: Getting VM IP...")
         time.sleep(1)
         log_queue.put("PROGRESS: Waiting for SSH (admin user)...")
         time.sleep(3)
         log_queue.put("PROGRESS: Running useradd command...")
         time.sleep(2)
         log_queue.put("PROGRESS: Creating .ssh directory...")
         time.sleep(1)
         log_queue.put("PROGRESS: Writing authorized_keys...")
         time.sleep(2)
         log_queue.put("PROGRESS: Setting permissions...")
         time.sleep(1)
         log_queue.put("PROGRESS: Verifying SSH as new user...")
         time.sleep(3)
         # Simulate success or failure
         import random
         if random.choice([True, False]):
             log_queue.put("RESULT:SUCCESS:User setup completed successfully!")
         else:
             log_queue.put("RESULT:FAILURE:User setup failed during permission setting.")
             log_queue.put("LOG: User setup finished with errors.")


    def run_challenge(self, log_queue, challenge_id, vm_name, snapshot_name, challenges_dir, ssh_user, ssh_key, simulate, keep_snapshot, verbose, libvirt_uri):
        log_queue.put(f"LOG: Starting challenge '{challenge_id}' on '{vm_name}'...")
        log_queue.put(f"LOG:  > Snapshot: '{snapshot_name}', User: '{ssh_user}', Key: '{ssh_key}'")
        log_queue.put(f"LOG:  > Simulate: {simulate}, Keep Snapshot: {keep_snapshot}, Verbose: {verbose}")
        time.sleep(0.5)
        log_queue.put("PROGRESS: Loading challenge details...")
        time.sleep(1)
        log_queue.put("PROGRESS: Connecting to libvirt...")
        time.sleep(1)
        log_queue.put("PROGRESS: Checking for existing snapshot...")
        time.sleep(1)
        log_queue.put("PROGRESS: Creating snapshot '{snapshot_name}'...")
        time.sleep(3)
        log_queue.put("PROGRESS: Starting VM...")
        time.sleep(2)
        log_queue.put("PROGRESS: Getting VM IP...")
        time.sleep(1)
        log_queue.put("PROGRESS: Waiting for SSH...")
        time.sleep(3)
        log_queue.put("PROGRESS: Displaying challenge info...")
        log_queue.put("LOG: === Challenge: Example Challenge ===") # Replace with actual details
        log_queue.put("LOG: Objective: Configure the hostname to 'practice-server'.")
        time.sleep(1)
        log_queue.put("PROGRESS: Running setup steps (if any)...")
        time.sleep(2)
        if simulate:
            log_queue.put("PROGRESS: Simulating user action...")
            time.sleep(2)
        else:
            log_queue.put("USER_ACTION: Please perform the required actions on the VM. Click 'Validate' when ready.")
            # In a real app, you'd likely disable/enable the Validate button here
            return # Stop the placeholder thread until user clicks Validate

        log_queue.put("PROGRESS: Starting validation...")
        time.sleep(1)
        log_queue.put("PROGRESS: Validation Step 1: Check hostname command...")
        time.sleep(2)
        # Simulate pass/fail
        import random
        passed = random.choice([True, False])
        if passed:
            log_queue.put("PROGRESS: Validation Step 1 Passed.")
            log_queue.put("RESULT:SUCCESS:Challenge PASSED! Score: 90/100") # Example score
        else:
            log_queue.put("PROGRESS: Validation Step 1 FAILED: Expected exit status 0, got 1.")
            log_queue.put("RESULT:FAILURE:Challenge FAILED. Score: 0/100")

        log_queue.put("PROGRESS: Starting cleanup...")
        time.sleep(1)
        if not keep_snapshot:
            log_queue.put("PROGRESS: Reverting snapshot...")
            time.sleep(3)
            log_queue.put("PROGRESS: Deleting snapshot...")
            time.sleep(2)
        else:
             log_queue.put("LOG: Keeping snapshot as requested.")
        log_queue.put("PROGRESS: Closing libvirt connection...")
        time.sleep(1)
        log_queue.put("LOG: Challenge workflow finished.")

    def create_template(self, log_queue, output_file):
        log_queue.put(f"LOG: Creating challenge template at '{output_file}'...")
        time.sleep(0.5)
        # Simulate file creation
        try:
             with open(output_file, "w") as f:
                 f.write("# Placeholder Challenge Template\n")
                 f.write("id: new-challenge\n")
                 f.write("name: New Challenge\n")
                 f.write("description: Describe the objective.\n")
                 f.write("validation:\n")
                 f.write("  - type: run_command\n")
                 f.write("    command: \"echo 'Validate me!'\"\n")
             log_queue.put(f"RESULT:SUCCESS:Template created: {output_file}")
        except Exception as e:
             log_queue.put(f"RESULT:FAILURE:Failed to create template: {e}")


    def validate_challenge_file(self, log_queue, file_path):
        log_queue.put(f"LOG: Validating challenge file: '{file_path}'...")
        time.sleep(1.5)
        # Simulate validation
        import random
        if random.choice([True, True, False]): # Higher chance of success
             log_queue.put(f"RESULT:SUCCESS:Validation successful for {Path(file_path).name}")
        else:
             log_queue.put(f"RESULT:FAILURE:Validation failed for {Path(file_path).name}: Missing 'description' key.")

# --- Main GUI Application Class ---
class LPEM_GUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Linux+ Practice Environment Manager (LPEM)")
        self.geometry("1100x700")
        ctk.set_appearance_mode("System") # Modes: "System" (default), "Dark", "Light"
        ctk.set_default_color_theme("blue") # Themes: "blue" (default), "green", "dark-blue"

        self.config_file = Path("lpem_gui_config.json")
        self.backend = BackendPlaceholder() # Instantiate your backend interface
        self.log_queue = queue.Queue()
        self.active_threads = []

        # --- Main Layout ---
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- Sidebar ---
        self.sidebar_frame = ctk.CTkFrame(self, width=250, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=4, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(6, weight=1) # Push elements up

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="LPEM Control", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        # VM Section
        self.vm_label = ctk.CTkLabel(self.sidebar_frame, text="Virtual Machines", anchor="w")
        self.vm_label.grid(row=1, column=0, padx=20, pady=(10, 0))
        self.vm_refresh_button = ctk.CTkButton(self.sidebar_frame, text="Refresh VMs", command=self._refresh_vms)
        self.vm_refresh_button.grid(row=2, column=0, padx=20, pady=5)
        self.vm_list_frame = ctk.CTkScrollableFrame(self.sidebar_frame, label_text="Available VMs", height=150)
        self.vm_list_frame.grid(row=3, column=0, padx=20, pady=(0, 10), sticky="nsew")
        self.vm_list_frame.grid_columnconfigure(0, weight=1)
        self.selected_vm = ctk.StringVar(value="") # Variable to hold selected VM
        self.vm_radio_buttons = [] # Store radio buttons

        # Challenge Section
        self.challenge_label = ctk.CTkLabel(self.sidebar_frame, text="Challenges", anchor="w")
        self.challenge_label.grid(row=4, column=0, padx=20, pady=(10, 0))
        # --- Challenge Dir Selection ---
        self.challenge_dir_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        self.challenge_dir_frame.grid(row=5, column=0, padx=20, pady=5, sticky="ew")
        self.challenge_dir_frame.grid_columnconfigure(0, weight=1)
        self.challenge_dir_entry = ctk.CTkEntry(self.challenge_dir_frame, placeholder_text="Challenges Directory")
        self.challenge_dir_entry.grid(row=0, column=0, sticky="ew", padx=(0,5))
        self.challenge_dir_button = ctk.CTkButton(self.challenge_dir_frame, text="...", width=30, command=self._select_challenge_dir)
        self.challenge_dir_button.grid(row=0, column=1)
        # -----------------------------
        self.challenge_refresh_button = ctk.CTkButton(self.sidebar_frame, text="Refresh Challenges", command=self._refresh_challenges)
        self.challenge_refresh_button.grid(row=6, column=0, padx=20, pady=5)
        self.challenge_list_frame = ctk.CTkScrollableFrame(self.sidebar_frame, label_text="Available Challenges", height=150)
        self.challenge_list_frame.grid(row=7, column=0, padx=20, pady=(0, 10), sticky="nsew")
        self.challenge_list_frame.grid_columnconfigure(0, weight=1)
        self.selected_challenge = ctk.StringVar(value="") # Variable to hold selected challenge
        self.challenge_radio_buttons = [] # Store radio buttons

        # Action Buttons
        self.run_challenge_button = ctk.CTkButton(self.sidebar_frame, text="Run Challenge", command=self._run_challenge)
        self.run_challenge_button.grid(row=8, column=0, padx=20, pady=10)

        self.setup_user_button = ctk.CTkButton(self.sidebar_frame, text="Setup VM User", command=self._setup_user)
        self.setup_user_button.grid(row=9, column=0, padx=20, pady=5)

        self.validate_button = ctk.CTkButton(self.sidebar_frame, text="Validate (User Action)", command=self._continue_challenge_validation)
        self.validate_button.grid(row=10, column=0, padx=20, pady=5)
        self.validate_button.configure(state="disabled") # Disabled initially

        # Challenge Management Buttons
        self.challenge_manage_label = ctk.CTkLabel(self.sidebar_frame, text="Challenge Tools", anchor="w")
        self.challenge_manage_label.grid(row=11, column=0, padx=20, pady=(10, 0))
        self.create_template_button = ctk.CTkButton(self.sidebar_frame, text="Create Template", command=self._create_template)
        self.create_template_button.grid(row=12, column=0, padx=20, pady=5)
        self.validate_challenge_button = ctk.CTkButton(self.sidebar_frame, text="Validate File", command=self._validate_challenge_file)
        self.validate_challenge_button.grid(row=13, column=0, padx=20, pady=5)


        # --- Main Area (Tabs) ---
        self.tabview = ctk.CTkTabview(self, width=800)
        self.tabview.grid(row=0, column=1, padx=(20, 20), pady=(20, 20), sticky="nsew")
        self.tabview.add("Output Log")
        self.tabview.add("Configuration")

        # Output Log Tab
        self.tabview.tab("Output Log").grid_columnconfigure(0, weight=1)
        self.tabview.tab("Output Log").grid_rowconfigure(0, weight=1)
        self.output_log = ctk.CTkTextbox(self.tabview.tab("Output Log"), state="disabled", wrap="word", font=("monospace", 12))
        self.output_log.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        # Configuration Tab
        self.tabview.tab("Configuration").grid_columnconfigure(1, weight=1)
        # Add some padding
        self.tabview.tab("Configuration").grid_rowconfigure(6, weight=1) # Push up
        self.tabview.tab("Configuration").grid_columnconfigure(2, weight=1) # Pad right

        config_row = 0
        # Libvirt URI
        ctk.CTkLabel(self.tabview.tab("Configuration"), text="Libvirt URI:").grid(row=config_row, column=0, padx=10, pady=5, sticky="w")
        self.config_libvirt_uri = ctk.CTkEntry(self.tabview.tab("Configuration"), width=400)
        self.config_libvirt_uri.grid(row=config_row, column=1, padx=10, pady=5, sticky="ew")
        config_row += 1

        # Default VM Name
        ctk.CTkLabel(self.tabview.tab("Configuration"), text="Default VM Name:").grid(row=config_row, column=0, padx=10, pady=5, sticky="w")
        self.config_default_vm = ctk.CTkEntry(self.tabview.tab("Configuration"), width=250)
        self.config_default_vm.grid(row=config_row, column=1, padx=10, pady=5, sticky="w")
        config_row += 1

        # Default SSH User
        ctk.CTkLabel(self.tabview.tab("Configuration"), text="Default SSH User:").grid(row=config_row, column=0, padx=10, pady=5, sticky="w")
        self.config_default_user = ctk.CTkEntry(self.tabview.tab("Configuration"), width=250)
        self.config_default_user.grid(row=config_row, column=1, padx=10, pady=5, sticky="w")
        config_row += 1

        # Default SSH Key Path
        ctk.CTkLabel(self.tabview.tab("Configuration"), text="Default SSH Key:").grid(row=config_row, column=0, padx=10, pady=5, sticky="w")
        self.config_key_frame = ctk.CTkFrame(self.tabview.tab("Configuration"), fg_color="transparent")
        self.config_key_frame.grid(row=config_row, column=1, padx=10, pady=5, sticky="ew")
        self.config_key_frame.grid_columnconfigure(0, weight=1)
        self.config_ssh_key = ctk.CTkEntry(self.config_key_frame, width=350)
        self.config_ssh_key.grid(row=0, column=0, sticky="ew", padx=(0,5))
        self.config_key_button = ctk.CTkButton(self.config_key_frame, text="...", width=30, command=self._select_ssh_key)
        self.config_key_button.grid(row=0, column=1)
        config_row += 1

        # Default Challenges Dir
        ctk.CTkLabel(self.tabview.tab("Configuration"), text="Challenges Dir:").grid(row=config_row, column=0, padx=10, pady=5, sticky="w")
        self.config_challenges_frame = ctk.CTkFrame(self.tabview.tab("Configuration"), fg_color="transparent")
        self.config_challenges_frame.grid(row=config_row, column=1, padx=10, pady=5, sticky="ew")
        self.config_challenges_frame.grid_columnconfigure(0, weight=1)
        self.config_challenges_dir = ctk.CTkEntry(self.config_challenges_frame, width=350)
        self.config_challenges_dir.grid(row=0, column=0, sticky="ew", padx=(0,5))
        self.config_challenges_dir_button = ctk.CTkButton(self.config_challenges_frame, text="...", width=30, command=self._select_challenges_config_dir)
        self.config_challenges_dir_button.grid(row=0, column=1)
        config_row += 1

        # Save Button
        self.save_config_button = ctk.CTkButton(self.tabview.tab("Configuration"), text="Save Configuration", command=self._save_config)
        self.save_config_button.grid(row=config_row, column=0, columnspan=2, padx=10, pady=20)

        # --- Initial Actions ---
        self._load_config() # Load config on startup
        self._update_challenge_dir_from_config() # Populate sidebar challenge dir
        self._start_queue_processor() # Start checking the queue
        self._refresh_vms() # Load initial VM list
        self._refresh_challenges() # Load initial challenge list

        self.protocol("WM_DELETE_WINDOW", self._on_closing) # Handle window close


    def _log_message(self, message):
        """Appends a message to the output log textbox."""
        self.output_log.configure(state="normal")
        self.output_log.insert("end", f"{message}\n")
        self.output_log.configure(state="disabled")
        self.output_log.see("end") # Auto-scroll

    def _process_log_queue(self):
        """Processes messages from the backend thread queue."""
        try:
            while True: # Process all available messages
                msg = self.log_queue.get_nowait()

                if msg.startswith("LOG:"):
                    self._log_message(msg[4:])
                elif msg.startswith("PROGRESS:"):
                     self._log_message(f"[{msg[9:]}]")
                elif msg.startswith("RESULT:SUCCESS:"):
                     self._log_message(f"✅ SUCCESS: {msg[15:]}")
                     self.validate_button.configure(state="disabled") # Re-disable on completion
                elif msg.startswith("RESULT:FAILURE:"):
                     self._log_message(f"❌ FAILURE: {msg[16:]}")
                     self.validate_button.configure(state="disabled") # Re-disable on completion
                elif msg.startswith("VMS_UPDATE:"):
                     vms = msg[11:].split(',') if msg[11:] else []
                     self._update_vm_list(vms)
                elif msg.startswith("CHALLENGES_UPDATE:"):
                     challenges = msg[18:].split(',') if msg[18:] else []
                     self._update_challenge_list(challenges)
                elif msg.startswith("USER_ACTION:"):
                     self._log_message(f"👉 ACTION REQUIRED: {msg[12:]}")
                     self.validate_button.configure(state="normal") # Enable validate button
                elif msg == "THREAD_DONE":
                    self.active_threads.pop(0) # Remove the finished thread indicator
                    # Optional: Re-enable buttons if needed
                else:
                    self._log_message(f"Unknown message: {msg}")

                self.log_queue.task_done()
        except queue.Empty:
            pass # No messages left
        finally:
            # Schedule the next check
            self.after(100, self._process_log_queue)

    def _start_queue_processor(self):
        """Starts the loop to process the log queue."""
        self.after(100, self._process_log_queue)

    def _run_backend_task(self, target_func, *args):
        """Wrapper to run a backend function in a thread and signal completion."""
        try:
            target_func(self.log_queue, *args)
        except Exception as e:
            self.log_queue.put(f"RESULT:FAILURE:Thread error: {e}")
            import traceback
            self.log_queue.put(f"LOG: Traceback:\n{traceback.format_exc()}")
        finally:
            self.log_queue.put("THREAD_DONE")

    def _start_thread(self, target_func, *args):
         """Starts a backend task in a new thread."""
         # Optional: Disable buttons while a thread is running
         thread = threading.Thread(target=self._run_backend_task, args=(target_func,) + args, daemon=True)
         self.active_threads.append(thread) # Keep track (optional)
         thread.start()


    # --- VM List Handling ---
    def _refresh_vms(self):
        """Requests an update to the VM list from the backend."""
        uri = self.config_libvirt_uri.get() or "qemu:///system" # Use config or default
        self._clear_vm_list()
        self._log_message("Refreshing VM list...")
        self._start_thread(self.backend.list_vms, uri)

    def _clear_vm_list(self):
        for widget in self.vm_list_frame.winfo_children():
            widget.destroy()
        self.vm_radio_buttons = []
        self.selected_vm.set("")

    def _update_vm_list(self, vm_names):
        """Populates the sidebar list with VM names."""
        self._clear_vm_list()
        for name in vm_names:
            rb = ctk.CTkRadioButton(self.vm_list_frame, text=name, variable=self.selected_vm, value=name)
            rb.grid(sticky="w", padx=5, pady=2)
            self.vm_radio_buttons.append(rb)
        if vm_names:
             self.selected_vm.set(vm_names[0]) # Select first one by default

    # --- Challenge List Handling ---
    def _select_challenge_dir(self):
        """Opens a dialog to select the challenges directory."""
        dir_path = filedialog.askdirectory(title="Select Challenges Directory")
        if dir_path:
            self.challenge_dir_entry.delete(0, "end")
            self.challenge_dir_entry.insert(0, dir_path)
            self._refresh_challenges() # Refresh list after selecting new dir

    def _refresh_challenges(self):
        """Requests an update to the challenge list from the backend."""
        challenges_dir = self.challenge_dir_entry.get()
        if not challenges_dir or not Path(challenges_dir).is_dir():
            self._log_message("ERROR: Please select a valid challenges directory first.")
            self._clear_challenge_list()
            return
        self._clear_challenge_list()
        self._log_message(f"Refreshing challenges from {challenges_dir}...")
        self._start_thread(self.backend.list_challenges, challenges_dir)

    def _clear_challenge_list(self):
         for widget in self.challenge_list_frame.winfo_children():
            widget.destroy()
         self.challenge_radio_buttons = []
         self.selected_challenge.set("")

    def _update_challenge_list(self, challenge_ids):
        """Populates the sidebar list with challenge IDs."""
        self._clear_challenge_list()
        for cid in challenge_ids:
            rb = ctk.CTkRadioButton(self.challenge_list_frame, text=cid, variable=self.selected_challenge, value=cid)
            rb.grid(sticky="w", padx=5, pady=2)
            self.challenge_radio_buttons.append(rb)
        if challenge_ids:
             self.selected_challenge.set(challenge_ids[0]) # Select first one

    # --- Action Button Callbacks ---
    def _run_challenge(self):
        """Starts the 'run-challenge' backend process."""
        vm = self.selected_vm.get()
        challenge_id = self.selected_challenge.get()
        challenges_dir = self.challenge_dir_entry.get()
        ssh_user = self.config_default_user.get() or "roo"
        ssh_key = self.config_ssh_key.get() or "~/.ssh/id_ed25519"
        libvirt_uri = self.config_libvirt_uri.get() or "qemu:///system"

        if not vm:
            self._log_message("ERROR: No VM selected.")
            return
        if not challenge_id:
            self._log_message("ERROR: No challenge selected.")
            return
        if not challenges_dir or not Path(challenges_dir).is_dir():
            self._log_message("ERROR: Invalid challenges directory selected.")
            return
        if not ssh_key:
             self._log_message("ERROR: SSH key path is missing in configuration.")
             return

        self.validate_button.configure(state="disabled") # Disable validate button initially
        self._log_message(f"Starting challenge '{challenge_id}' on VM '{vm}'...")
        # Placeholder args for simulate, keep_snapshot, verbose - could add checkboxes later
        self._start_thread(self.backend.run_challenge, challenge_id, vm, "gui_snapshot", challenges_dir, ssh_user, ssh_key, False, False, False, libvirt_uri)

    def _setup_user(self):
        """Starts the 'setup-user' backend process."""
        vm = self.selected_vm.get()
        # Get config values, provide defaults if empty
        new_user = self.config_default_user.get() or "roo" # Setup the default user
        admin_user = "ubuntu" # Hardcode admin user for placeholder - make configurable?
        admin_key = self.config_ssh_key.get() or "~/.ssh/id_ed25519" # Assume admin uses same key
        libvirt_uri = self.config_libvirt_uri.get() or "qemu:///system"
        # Derive public key path from private key path - simplistic approach
        private_key_path = Path(admin_key).expanduser()
        public_key_path = private_key_path.with_suffix(".pub")

        if not vm:
            self._log_message("ERROR: No VM selected.")
            return
        if not admin_key:
             self._log_message("ERROR: SSH key path is missing in configuration (needed for admin).")
             return
        if not public_key_path.exists():
             self._log_message(f"ERROR: Cannot find public key '{public_key_path}' needed for setup.")
             return

        self._log_message(f"Starting user setup for '{new_user}' on VM '{vm}'...")
        self._start_thread(self.backend.setup_user, vm, new_user, admin_user, admin_key, str(public_key_path), libvirt_uri)

    def _continue_challenge_validation(self):
        """Signals the running challenge thread (via queue) to proceed with validation."""
        self._log_message("User requested validation to proceed...")
        # In a real implementation, you might need a more sophisticated way
        # to signal the specific backend thread if multiple could run.
        # For this placeholder, we assume the run_challenge placeholder handles it.
        self.backend.run_challenge(self.log_queue, # Resuming the placeholder logic
             self.selected_challenge.get(), self.selected_vm.get(),
             "gui_snapshot", self.challenge_dir_entry.get(),
             self.config_default_user.get() or "roo",
             self.config_ssh_key.get() or "~/.ssh/id_ed25519",
             False, False, False, self.config_libvirt_uri.get() or "qemu:///system"
        )
        self.validate_button.configure(state="disabled") # Disable after clicking

    def _create_template(self):
        """Asks for filename and runs the create-template backend action."""
        file_path = filedialog.asksaveasfilename(
            title="Save Challenge Template As",
            defaultextension=".yaml",
            filetypes=[("YAML files", "*.yaml"), ("All files", "*.*")]
        )
        if file_path:
             self._log_message(f"Requesting template creation at {file_path}...")
             self._start_thread(self.backend.create_template, file_path)


    def _validate_challenge_file(self):
        """Asks for file and runs the validate-challenge backend action."""
        file_path = filedialog.askopenfilename(
            title="Select Challenge File to Validate",
            filetypes=[("YAML files", "*.yaml"), ("All files", "*.*")]
        )
        if file_path:
            self._log_message(f"Requesting validation for {file_path}...")
            self._start_thread(self.backend.validate_challenge_file, file_path)


    # --- Configuration Handling ---
    def _select_ssh_key(self):
        """Opens dialog to select SSH private key file."""
        # Start in user's .ssh directory if it exists
        ssh_dir = Path.home() / ".ssh"
        initial_dir = str(ssh_dir) if ssh_dir.is_dir() else str(Path.home())
        file_path = filedialog.askopenfilename(title="Select Default SSH Private Key", initialdir=initial_dir)
        if file_path:
            self.config_ssh_key.delete(0, "end")
            self.config_ssh_key.insert(0, file_path)

    def _select_challenges_config_dir(self):
        """Opens dialog to select challenges directory for config tab."""
        dir_path = filedialog.askdirectory(title="Select Default Challenges Directory")
        if dir_path:
            self.config_challenges_dir.delete(0, "end")
            self.config_challenges_dir.insert(0, dir_path)

    def _load_config(self):
        """Loads configuration from the JSON file."""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    config_data = json.load(f)

                self.config_libvirt_uri.insert(0, config_data.get("libvirt_uri", "qemu:///system"))
                self.config_default_vm.insert(0, config_data.get("default_vm", "ubuntu24.04-2"))
                self.config_default_user.insert(0, config_data.get("default_user", "roo"))
                self.config_ssh_key.insert(0, config_data.get("ssh_key_path", "~/.ssh/id_ed25519"))
                self.config_challenges_dir.insert(0, config_data.get("challenges_dir", "./challenges"))
                self._log_message(f"Configuration loaded from {self.config_file}")
            else:
                 self._log_message("Configuration file not found. Using defaults.")
                 # Populate with defaults if file doesn't exist
                 self.config_libvirt_uri.insert(0, "qemu:///system")
                 self.config_default_vm.insert(0, "ubuntu24.04-2")
                 self.config_default_user.insert(0, "roo")
                 self.config_ssh_key.insert(0, "~/.ssh/id_ed25519")
                 self.config_challenges_dir.insert(0, "./challenges")

        except (json.JSONDecodeError, IOError) as e:
            self._log_message(f"Error loading configuration: {e}. Using defaults.")
            # Ensure defaults are populated even if load fails
            if not self.config_libvirt_uri.get(): self.config_libvirt_uri.insert(0, "qemu:///system")
            if not self.config_default_vm.get(): self.config_default_vm.insert(0, "ubuntu24.04-2")
            if not self.config_default_user.get(): self.config_default_user.insert(0, "roo")
            if not self.config_ssh_key.get(): self.config_ssh_key.insert(0, "~/.ssh/id_ed25519")
            if not self.config_challenges_dir.get(): self.config_challenges_dir.insert(0, "./challenges")


    def _save_config(self):
        """Saves current configuration settings to the JSON file."""
        config_data = {
            "libvirt_uri": self.config_libvirt_uri.get(),
            "default_vm": self.config_default_vm.get(),
            "default_user": self.config_default_user.get(),
            "ssh_key_path": self.config_ssh_key.get(),
            "challenges_dir": self.config_challenges_dir.get(),
        }
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config_data, f, indent=4)
            self._log_message(f"Configuration saved to {self.config_file}")
            self._update_challenge_dir_from_config() # Update sidebar dir if changed
        except IOError as e:
            self._log_message(f"Error saving configuration: {e}")

    def _update_challenge_dir_from_config(self):
         """Sets the sidebar challenge directory from the loaded config."""
         config_dir = self.config_challenges_dir.get()
         if config_dir:
              self.challenge_dir_entry.delete(0, "end")
              self.challenge_dir_entry.insert(0, config_dir)


    def _on_closing(self):
        """Handle window closing event."""
        # Optional: Add checks for running threads or confirmation dialog
        print("Closing LPEM GUI.")
        self.destroy()


if __name__ == "__main__":
    app = LPEM_GUI()
    app.mainloop()
