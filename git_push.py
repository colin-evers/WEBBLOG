#!/usr/bin/env python3
"""
===============================================================================
Git Automation Assistant for WebBlog
===============================================================================
A step-by-step graphical automation tool for inspecting, synchronizing,
staging, committing, pushing, and verifying Git repository changes with
integrated error handling, rollback safety, and a standardized GUI.

Workflow Overview (5 Steps):
-------------------------------------------------------------------------------
1. Step 1 of 5: Initial Repository Pre-Check (Fetch & Status)
   - Executes: `git fetch` (synchronizes remote branch state) followed by `git status`.
   - Discrepancy Detection:
     * If local is UP-TO-DATE & CLEAN (nothing to commit): Displays ONLY the [ Exit ] button.
     * If local has MODIFICATIONS to commit: Displays standard [ Next ] and [ Cancel / Exit ] buttons.
     * If local is BEHIND remote: Displays warning badge and presents two explicit choices:
        - [ Pull & Proceed ] (Green): Safely stashes all tracked & untracked files (`git stash push -u`),
          rebases remote commits (`git pull --rebase`), and restores local edits (`git stash pop`).
          If no local changes exist after pulling, shows a synchronized confirmation with ONLY an [ Exit ] button.
          If uncommitted local changes exist, seamlessly proceeds to Step 2.
        - [ Exit ]: Closes the application immediately without altering the repository.

2. Step 2 of 5: Staging All Changes
   - Executes: `git add -A` (stages all modified, deleted, and untracked files).
   - Safe Cancellation: Executes `git restore --staged .` to unstage all files,
     delays 1.0 second with on-screen confirmation, and exits cleanly.

3. Step 3 of 5: Commit Message Entry & Commit
   - Prompts the user with a focused 680x480 text input dialog.
   - Highlights the prominent green [ Next ] button (activated via click or Enter key).
   - Executes: `git commit -m "<COMMENT>"`.
   - Safe Cancellation: Executes `git reset --soft HEAD~1` followed by
     `git restore --staged .` to undo the commit and unstaging while keeping
     all local source file edits 100% intact in the working directory.

4. Step 4 of 5: Updating Remote Repository (Push)
   - Executes: `git push origin -u <branch>`.
   - Safe Cancellation: Executes `git reset --soft HEAD~1`, `git restore --staged .`,
     and `git push --force-with-lease origin <branch>` to roll back the remote GitHub
     repository by 1 commit while preserving all local modifications intact.

5. Step 5 of 5: Final Post-Update Status
   - Executes: `git status` to verify the repository is clean and fully synchronized.
   - Action Buttons:
     * [ Exit ]: Completes workflow and closes the application cleanly.
     * [ Cancel ]: Rolls back remote repository (`git push --force-with-lease`)
       and undoes local commit/staging (`git reset --soft HEAD~1` + `git restore --staged .`),
       leaving all working directory file edits intact.

GUI Features:
-------------------------------------------------------------------------------
- Fixed 680x480 geometry with identical screen-centered coordinates for every step.
- Bottom-pinned button bars that cannot be clipped by DPI display scaling or text overflow.
- High-contrast, responsive action buttons with full keyboard support (<Return>, Space).
===============================================================================
"""

import os
import sys
import time
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox


def run_git_command(command, cwd=None):
    """
    Executes a shell git command within the specified working directory.

    Args:
        command (str): The git command line string to execute.
        cwd (str, optional): The directory where the command is executed.
                             Defaults to the repository root of this script.

    Returns:
        tuple: (returncode: int, stdout: str, stderr: str)
    """
    if cwd is None:
        cwd = os.path.dirname(os.path.abspath(__file__))
    try:
        process = subprocess.Popen(
            command,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=True
        )
        stdout, stderr = process.communicate()
        return process.returncode, stdout.strip(), stderr.strip()
    except Exception as e:
        return -1, "", str(e)


def get_current_branch(repo_dir):
    """
    Detects and returns the active Git branch name.

    Args:
        repo_dir (str): Absolute path to the local git repository.

    Returns:
        str: Current branch name (e.g. 'master', 'main'). Defaults to 'master'.
    """
    code, out, _ = run_git_command("git branch --show-current", cwd=repo_dir)
    if code == 0 and out:
        return out
    code, out, _ = run_git_command("git rev-parse --abbrev-ref HEAD", cwd=repo_dir)
    return out if (code == 0 and out) else "master"


class GitStepDialog:
    """
    Standardized, modal step dialog for executing and displaying Git operations.

    Features:
    - Guaranteed 680x480 dimensions centered on screen.
    - Pinned bottom button bar with [ Next ] / [ Exit ] and [ Cancel ] buttons.
    - Scrollable monospace output console displaying real-time command feedback.
    - Status badge showing execution state (Running, Success, Error).
    - Keyboard navigation (<Return>, <KP_Enter>, <Space>).
    """

    def __init__(self, parent, title, step_num, command_str, on_cancel_callback=None):
        self.parent = parent
        self.on_cancel_callback = on_cancel_callback
        self.top = tk.Toplevel(parent)
        self.top.title(f"Git Automation - Step {step_num}")
        self.top.geometry("680x480")
        self.top.minsize(550, 380)
        self.top.attributes('-topmost', True)
        self.top.protocol("WM_DELETE_WINDOW", self.on_close)
        self.result_proceed = False
        self.is_cancelling = False

        # Center the window on user screen
        self.center_window()

        # Outer layout container
        main_frame = tk.Frame(self.top, bg="#FFFFFF", padx=16, pady=16)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 1. Header Title Label
        lbl_title = tk.Label(
            main_frame,
            text=title,
            font=("Segoe UI", 13, "bold"),
            bg="#FFFFFF",
            fg="#1F4E78"
        )
        lbl_title.pack(anchor="w", pady=(0, 6))

        # 2. Command Display Box
        cmd_frame = tk.Frame(main_frame, bg="#E9EEF4", bd=1, relief="solid")
        cmd_frame.pack(fill=tk.X, pady=(0, 10))
        self.lbl_cmd = tk.Label(
            cmd_frame,
            text=f"Command:  {command_str}",
            font=("Consolas", 10, "bold"),
            bg="#E9EEF4",
            fg="#0F4C81",
            padx=10,
            pady=8
        )
        self.lbl_cmd.pack(anchor="w")

        # 3. Bottom Button Bar (Pinned to BOTTOM so it is never pushed off-screen)
        bottom_frame = tk.Frame(main_frame, bg="#FFFFFF")
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(12, 0))

        self.lbl_status = tk.Label(
            bottom_frame,
            text="Executing...",
            font=("Segoe UI", 10, "bold"),
            bg="#FFFFFF",
            fg="#555555"
        )
        self.lbl_status.pack(side=tk.LEFT)

        # Action / Next Button (Prominent, styled, always visible)
        self.btn_ok = tk.Button(
            bottom_frame,
            text="  Next  ",
            font=("Segoe UI", 11, "bold"),
            bg="#1F4E78",
            fg="#FFFFFF",
            activebackground="#143452",
            activeforeground="#FFFFFF",
            relief="raised",
            bd=2,
            padx=18,
            pady=4,
            command=self.on_ok,
            cursor="hand2"
        )
        self.btn_ok.pack(side=tk.RIGHT, padx=(8, 0))

        # Cancel / Exit Button
        self.btn_cancel = tk.Button(
            bottom_frame,
            text="Cancel / Exit",
            font=("Segoe UI", 10),
            bg="#E1E4E8",
            fg="#24292F",
            relief="raised",
            bd=1,
            padx=12,
            pady=4,
            command=self.on_close,
            cursor="hand2"
        )
        self.btn_cancel.pack(side=tk.RIGHT)

        # 4. Monospace Command Output Console (Fills remaining central space)
        lbl_out = tk.Label(
            main_frame,
            text="Command Output / Result:",
            font=("Segoe UI", 10, "bold"),
            bg="#FFFFFF",
            fg="#333333"
        )
        lbl_out.pack(anchor="w", pady=(0, 4))

        text_frame = tk.Frame(main_frame, bd=1, relief="solid")
        text_frame.pack(fill=tk.BOTH, expand=True)

        self.txt_output = tk.Text(
            text_frame,
            wrap=tk.WORD,
            font=("Consolas", 10),
            bg="#FAFAFA",
            fg="#24292F",
            bd=0,
            padx=8,
            pady=8
        )
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.txt_output.yview)
        self.txt_output.configure(yscrollcommand=scrollbar.set)

        self.txt_output.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Key bindings for keyboard operation
        self.top.bind("<Return>", lambda e: self.on_ok())
        self.top.bind("<KP_Enter>", lambda e: self.on_ok())

    def center_window(self):
        """Calculates and positions the window in the center of the primary monitor"""
        self.top.update_idletasks()
        w = 680
        h = 480
        x = (self.top.winfo_screenwidth() // 2) - (w // 2)
        y = (self.top.winfo_screenheight() // 2) - (h // 2)
        self.top.geometry(f"{w}x{h}+{x}+{y}")

    def set_result(self, code, stdout, stderr, custom_success_msg=None):
        """
        Updates the console text area and status badge with execution results.

        Args:
            code (int): Command return code (0 = success).
            stdout (str): Standard output from the command.
            stderr (str): Standard error from the command.
            custom_success_msg (str, optional): Fallback message when stdout is empty.
        """
        self.txt_output.delete("1.0", tk.END)
        content = []
        if stdout:
            content.append(stdout)
        if stderr:
            content.append(stderr)
        
        full_out = "\n".join(content).strip()
        if not full_out and code == 0 and custom_success_msg:
            full_out = custom_success_msg
        elif not full_out:
            full_out = "(Command completed with no text output)"

        self.txt_output.insert(tk.END, full_out)

        if code == 0:
            self.lbl_status.config(text="✔ SUCCESS", fg="#2E7D32")
            self.btn_ok.config(bg="#2E7D32", text="  Next  ")
        else:
            self.lbl_status.config(text=f"✖ ERROR (Exit code {code})", fg="#C62828")
            self.btn_ok.config(bg="#C62828", text="  Next (Continue)  ")

        self.btn_ok.focus_set()

    def on_ok(self):
        """Handles Next button click or Enter key to proceed to subsequent step"""
        if self.is_cancelling:
            return
        self.result_proceed = True
        self.top.destroy()

    def on_close(self):
        """Handles Cancel button click, window close button (X), or Escape"""
        if self.is_cancelling:
            return
        self.result_proceed = False
        if self.on_cancel_callback:
            self.is_cancelling = True
            self.btn_ok.config(state=tk.DISABLED)
            self.btn_cancel.config(state=tk.DISABLED)
            self.on_cancel_callback(self)
        else:
            self.top.destroy()


def prompt_commit_comment(parent):
    """
    Displays a standardized 680x480 modal dialog for entering the Git commit message.

    Features:
    - Centered 680x480 window layout matching all step dialogs.
    - Prominent green [ Next ] button (#2E7D32) triggered by mouse click or Enter.
    - Multi-line text entry box with automatic keyboard focus.
    - Validation preventing empty or whitespace-only commit messages.

    Args:
        parent: The root Tk application instance.

    Returns:
        str or None: The user's commit comment, or None if cancelled.
    """
    dlg = tk.Toplevel(parent)
    dlg.title("Git Automation - Step 3: Commit Comment")
    dlg.geometry("680x480")
    dlg.minsize(550, 380)
    dlg.attributes('-topmost', True)

    # Center window
    dlg.update_idletasks()
    w = 680
    h = 480
    x = (dlg.winfo_screenwidth() // 2) - (w // 2)
    y = (dlg.winfo_screenheight() // 2) - (h // 2)
    dlg.geometry(f"{w}x{h}+{x}+{y}")

    comment_result = {"val": None}

    main_frame = tk.Frame(dlg, bg="#FFFFFF", padx=16, pady=16)
    main_frame.pack(fill=tk.BOTH, expand=True)

    # Header Title
    lbl_title = tk.Label(
        main_frame,
        text="Step 3 of 5: Enter Commit Message / Comment",
        font=("Segoe UI", 13, "bold"),
        bg="#FFFFFF",
        fg="#1F4E78"
    )
    lbl_title.pack(anchor="w", pady=(0, 6))

    # Command Information Box
    cmd_frame = tk.Frame(main_frame, bg="#E9EEF4", bd=1, relief="solid")
    cmd_frame.pack(fill=tk.X, pady=(0, 12))
    lbl_cmd = tk.Label(
        cmd_frame,
        text='Command to execute:  git commit -m "<YOUR COMMENT>"',
        font=("Consolas", 10, "bold"),
        bg="#E9EEF4",
        fg="#0F4C81",
        padx=10,
        pady=8
    )
    lbl_cmd.pack(anchor="w")

    # Bottom Button Bar (Pinned to BOTTOM)
    bottom_frame = tk.Frame(main_frame, bg="#FFFFFF")
    bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(12, 0))

    lbl_status = tk.Label(
        bottom_frame,
        text="Awaiting commit comment...",
        font=("Segoe UI", 10, "bold"),
        bg="#FFFFFF",
        fg="#555555"
    )
    lbl_status.pack(side=tk.LEFT)

    def on_ok(event=None):
        val = txt_comment.get("1.0", tk.END).strip()
        if not val:
            messagebox.showwarning("Empty Comment", "Please enter a commit comment before proceeding.", parent=dlg)
            return "break"
        comment_result["val"] = val
        dlg.destroy()
        return "break"

    def on_cancel():
        dlg.destroy()

    # Prominent Green Next Button for Commit
    btn_next = tk.Button(
        bottom_frame,
        text="  Next  ",
        font=("Segoe UI", 11, "bold"),
        bg="#2E7D32",
        fg="#FFFFFF",
        activebackground="#1E5E24",
        activeforeground="#FFFFFF",
        relief="raised",
        bd=2,
        padx=18,
        pady=4,
        command=on_ok,
        cursor="hand2"
    )
    btn_next.pack(side=tk.RIGHT, padx=(8, 0))

    btn_cancel = tk.Button(
        bottom_frame,
        text="Cancel / Exit",
        font=("Segoe UI", 10),
        bg="#E1E4E8",
        fg="#24292F",
        relief="raised",
        bd=1,
        padx=12,
        pady=4,
        command=on_cancel,
        cursor="hand2"
    )
    btn_cancel.pack(side=tk.RIGHT)

    # Text Input Instruction Label
    lbl_input = tk.Label(
        main_frame,
        text="Type your commit description below (press Enter or click Next to proceed):",
        font=("Segoe UI", 10, "bold"),
        bg="#FFFFFF",
        fg="#333333"
    )
    lbl_input.pack(anchor="w", pady=(0, 4))

    text_frame = tk.Frame(main_frame, bd=1, relief="solid")
    text_frame.pack(fill=tk.BOTH, expand=True)

    txt_comment = tk.Text(
        text_frame,
        wrap=tk.WORD,
        font=("Segoe UI", 11),
        bg="#FAFAFA",
        fg="#24292F",
        bd=0,
        padx=10,
        pady=10
    )
    txt_comment.pack(fill=tk.BOTH, expand=True)
    txt_comment.focus_set()

    # Enter key shortcuts to proceed
    txt_comment.bind("<Return>", on_ok)
    txt_comment.bind("<KP_Enter>", on_ok)
    dlg.bind("<Return>", on_ok)
    dlg.bind("<KP_Enter>", on_ok)

    dlg.grab_set()
    parent.wait_window(dlg)
    return comment_result["val"]


def main():
    """
    Main orchestration controller executing the 5-step Git automation pipeline.
    """
    repo_dir = os.path.dirname(os.path.abspath(__file__))

    # Hidden root Tk instance
    root = tk.Tk()
    root.withdraw()

    # Detect current working branch
    branch = get_current_branch(repo_dir)

    # -------------------------------------------------------------------------
    # STEP 1 of 5: Repository Pre-Check (git fetch && git status)
    # -------------------------------------------------------------------------
    step1_cmd = "git fetch && git status"
    dlg1 = GitStepDialog(root, "Step 1 of 5: Repository Pre-Check (Fetch & Status)", 1, step1_cmd)
    root.update()

    # Execute fetch followed by status to detect any branch discrepancies
    code1_fetch, out1_fetch, err1_fetch = run_git_command("git fetch", cwd=repo_dir)
    code1_status, out1_status, err1_status = run_git_command("git status", cwd=repo_dir)

    combined_code1 = 0 if (code1_fetch == 0 and code1_status == 0) else (code1_status or code1_fetch)
    combined_out1 = []
    if out1_fetch:
        combined_out1.append(f"[git fetch output]:\n{out1_fetch}")
    if err1_fetch:
        combined_out1.append(f"[git fetch remote status]:\n{err1_fetch}")
    if out1_status:
        combined_out1.append(f"[git status output]:\n{out1_status}")
    if err1_status:
        combined_out1.append(f"[git status errors]:\n{err1_status}")

    # Check repository state conditions
    is_behind = "is behind" in out1_status.lower() or "have diverged" in out1_status.lower()
    is_clean = ("nothing to commit" in out1_status.lower() or "working tree clean" in out1_status.lower() or "working directory clean" in out1_status.lower())
    is_ahead = "is ahead" in out1_status.lower()
    is_clean_and_uptodate = is_clean and not is_behind and not is_ahead

    # Formulate safety explanation banner for the output window
    explanation_blocks = []
    if is_behind:
        explanation_blocks.append(
            "======================================================================\n"
            " UPSTREAM COMMITS DETECTED ON REMOTE REPOSITORY (BRANCH IS BEHIND)\n"
            "======================================================================\n"
            "HOW YOUR LOCAL CHANGES ARE PROTECTED AGAINST LOSS:\n"
            f"• If you click [ Pull & Proceed ], the script executes:\n"
            f"    1. 'git stash push -u' to safely stash all modified AND untracked files.\n"
            f"    2. 'git pull --rebase origin {branch}' to cleanly bring in remote commits.\n"
            f"    3. 'git stash pop' to restore all your uncommitted local edits on top.\n"
            "  ==> RESULT: Your local source code modifications are 100% preserved and safe.\n"
            "• If you click [ Exit ], the application closes and leaves the repository untouched.\n"
            "======================================================================"
        )
    elif is_clean_and_uptodate:
        explanation_blocks.append(
            "======================================================================\n"
            " REPOSITORY IS COMPLETELY UP TO DATE & CLEAN\n"
            "======================================================================\n"
            "• Your local branch is fully in-sync with the remote repository.\n"
            "• Working tree is clean: there are no modified or untracked files to commit.\n"
            "• No further action required. Click [ Exit ] to close.\n"
            "======================================================================"
        )
    else:
        explanation_blocks.append(
            "======================================================================\n"
            " REPOSITORY STATUS & LOCAL CHANGE SAFETY\n"
            "======================================================================\n"
            "• Your branch is up to date with the remote repository.\n"
            "• Any modified, added, or deleted files shown below will be staged in Step 2.\n"
            "• If you cancel at any subsequent stage, all local file edits remain intact.\n"
            "======================================================================"
        )

    if combined_out1:
        explanation_blocks.append("\n\n".join(combined_out1))
    else:
        explanation_blocks.append("Repository is up to date and clean.")

    full_text1 = "\n\n".join(explanation_blocks).strip()

    dlg1.set_result(combined_code1, full_text1, "")

    if is_clean_and_uptodate:
        # Nothing to commit, working tree clean -> No Next button, ONLY Exit button
        dlg1.lbl_status.config(text="✔ UP TO DATE & CLEAN (Nothing to commit)", fg="#2E7D32")
        dlg1.btn_ok.pack_forget()
        dlg1.btn_cancel.config(
            text="  Exit  ",
            bg="#1F4E78",
            fg="#FFFFFF",
            font=("Segoe UI", 11, "bold"),
            padx=18,
            pady=4
        )
        dlg1.btn_cancel.focus_set()
        dlg1.top.bind("<Return>", lambda e: dlg1.on_close())
        dlg1.top.bind("<KP_Enter>", lambda e: dlg1.on_close())
    elif is_behind:
        dlg1.lbl_status.config(text="⚠ BEHIND REMOTE (Upstream changes detected)", fg="#D97706")
        dlg1.btn_ok.config(text="  Pull & Proceed  ", bg="#2E7D32")
        dlg1.btn_cancel.config(text="Exit")
    else:
        dlg1.btn_ok.config(text="  Next  ")
        dlg1.btn_cancel.config(text="Cancel / Exit")

    root.wait_window(dlg1.top)

    if is_clean_and_uptodate or not dlg1.result_proceed:
        sys.exit(0)

    # If the repository was behind and user clicked 'Pull & Proceed', pull latest changes safely
    if is_behind:
        # Check if there are local uncommitted or untracked changes
        has_local_changes = bool(out1_status.strip() and "nothing to commit, working tree clean" not in out1_status.lower())
        did_stash = False

        # Stash all modified AND untracked files (using -u) so incoming remote files don't collide
        if has_local_changes:
            c_stash, out_stash, err_stash = run_git_command('git stash push -u -m "autostash_git_push"', cwd=repo_dir)
            if c_stash == 0 and "No local changes to save" not in out_stash:
                did_stash = True

        # Pull and rebase cleanly
        pull_cmd = f"git pull --rebase origin {branch}"
        code_pull, out_pull, err_pull = run_git_command(pull_cmd, cwd=repo_dir)

        # Restore local stashed modifications and untracked files
        if did_stash:
            c_pop, out_pop, err_pop = run_git_command("git stash pop", cwd=repo_dir)
            if c_pop != 0:
                messagebox.showwarning(
                    "Merge Conflict Markers Placed",
                    f"Remote changes were pulled, and Git has placed standard conflict markers (<<<<<<< / >>>>>>>) inside the conflicting file(s):\n\n"
                    f"{out_pop}\n{err_pop}\n\n"
                    "Please open the file(s) in your code editor, resolve the conflict markers, and re-run git_push.py.",
                    parent=root
                )
                sys.exit(1)

        if code_pull != 0:
            combined_err = f"{out_pull}\n{err_pull}".strip()
            if "untracked working tree files would be overwritten" in combined_err.lower():
                msg = (
                    "Git Safety Rule Notice:\n\n"
                    "• Git will never touch, modify, or insert conflict markers into an untracked file.\n"
                    "• Because local files exist untracked that also exist on the remote repository, Git has aborted the pull to protect your uncommitted work from being overwritten.\n\n"
                    "How to resolve this manually:\n"
                    "1. Move or rename your local untracked file(s) temporarily, OR\n"
                    "2. Stage the file with 'git add <file>', then pull to let Git perform a 3-way diff and insert conflict markers.\n\n"
                    f"Git Output:\n{combined_err}"
                )
                messagebox.showerror("Git Untracked File Safety Notice", msg, parent=root)
            else:
                messagebox.showerror(
                    "Pull Conflict / Error",
                    f"Failed to pull and rebase upstream changes automatically:\n\n{out_pull}\n{err_pull}\n\nPlease resolve conflicts manually.",
                    parent=root
                )
            sys.exit(1)

        # Check post-pull status to see if there are local uncommitted changes to proceed with
        c_post_status, out_post_status, _ = run_git_command("git status", cwd=repo_dir)
        is_clean_post_pull = (
            ("nothing to commit" in out_post_status.lower() or "working tree clean" in out_post_status.lower() or "working directory clean" in out_post_status.lower())
            and "is ahead" not in out_post_status.lower()
        )

        # If no local changes exist after pulling -> Show up-to-date dialog with ONLY Exit button
        if is_clean_post_pull:
            dlg_sync = GitStepDialog(root, "Repository Synchronized & Up to Date", 1, "git pull (Completed)")
            dlg_sync.lbl_status.config(text="✔ UP TO DATE & CLEAN (No local changes to commit)", fg="#2E7D32")
            dlg_sync.btn_ok.pack_forget()
            dlg_sync.btn_cancel.config(
                text="  Exit  ",
                bg="#1F4E78",
                fg="#FFFFFF",
                font=("Segoe UI", 11, "bold"),
                padx=18,
                pady=4
            )
            sync_text = (
                "======================================================================\n"
                " REPOSITORY SYNCHRONIZED SUCCESSFULLY\n"
                "======================================================================\n"
                "• All latest remote commits have been pulled and integrated.\n"
                "• Your local repository is now 100% up to date with the remote repository.\n"
                "• Working tree is clean: there are no local modifications to commit.\n"
                "• Click [ Exit ] to finish.\n"
                "======================================================================\n\n"
                f"[git pull output]:\n{out_pull or 'Already up to date.'}\n\n"
                f"[git status output]:\n{out_post_status}"
            )
            dlg_sync.set_result(0, sync_text, "")
            dlg_sync.btn_ok.pack_forget()
            dlg_sync.btn_cancel.focus_set()
            dlg_sync.top.bind("<Return>", lambda e: dlg_sync.on_close())
            dlg_sync.top.bind("<KP_Enter>", lambda e: dlg_sync.on_close())
            root.wait_window(dlg_sync.top)
            sys.exit(0)

    # -------------------------------------------------------------------------
    # STEP 2 of 5: Staging All Changes (git add -A)
    # -------------------------------------------------------------------------
    def step2_cancel_handler(dialog):
        """Rolls back staging via 'git restore --staged .' upon cancellation"""
        dialog.lbl_status.config(text="Cancelling... Executing git restore --staged .", fg="#C62828")
        dialog.txt_output.insert(tk.END, "\n\n[Action: Cancelled by user]\nExecuting: git restore --staged .\n")
        dialog.txt_output.see(tk.END)
        dialog.top.update()

        c, out, err = run_git_command("git restore --staged .", cwd=repo_dir)
        if c == 0:
            dialog.txt_output.insert(tk.END, "Result: All staged changes successfully restored/unstaged.\nExiting...")
        else:
            dialog.txt_output.insert(tk.END, f"Result:\n{out}\n{err}\nExiting...")

        dialog.txt_output.see(tk.END)
        dialog.lbl_status.config(text="Staged changes restored. Exiting in 1 second...", fg="#C62828")
        dialog.top.update()

        time.sleep(1.0)
        dialog.top.destroy()

    step2_cmd = "git add -A"
    dlg2 = GitStepDialog(root, "Step 2 of 5: Staging All Changes", 2, step2_cmd, on_cancel_callback=step2_cancel_handler)
    root.update()
    
    code2, out2, err2 = run_git_command(step2_cmd, cwd=repo_dir)
    dlg2.set_result(code2, out2, err2, custom_success_msg="All modified, deleted, and untracked files staged successfully.")
    root.wait_window(dlg2.top)

    if not dlg2.result_proceed:
        sys.exit(0)

    # -------------------------------------------------------------------------
    # STEP 3 of 5: Commit Message Entry & Commit (git commit -m "...")
    # -------------------------------------------------------------------------
    comment = prompt_commit_comment(root)
    if comment is None:
        # User aborted during comment input -> restore staged files
        run_git_command("git restore --staged .", cwd=repo_dir)
        messagebox.showinfo("Aborted", "Commit was cancelled. Staged changes restored.", parent=root)
        sys.exit(0)

    # Escape quotes for command execution
    escaped_comment = comment.replace('"', '\\"')
    step3_cmd = f'git commit -m "{escaped_comment}"'
    
    def step3_cancel_handler(dialog):
        """Undoes local commit and staging while preserving all working directory changes intact"""
        dialog.lbl_status.config(text="Backing out commit & unstaging changes...", fg="#C62828")
        dialog.txt_output.insert(tk.END, "\n\n[Action: Cancelled by user - Backing out Step 3]\n")
        dialog.txt_output.insert(tk.END, "1. Executing: git reset --soft HEAD~1\n")
        dialog.txt_output.see(tk.END)
        dialog.top.update()

        # 1. git reset --soft HEAD~1 (undoes commit, keeps changes staged)
        c1, out1, err1 = run_git_command("git reset --soft HEAD~1", cwd=repo_dir)
        if c1 == 0:
            dialog.txt_output.insert(tk.END, "   Result: Commit successfully undone (HEAD moved back 1 commit).\n")
        else:
            dialog.txt_output.insert(tk.END, f"   Result: {out1} {err1}\n")

        dialog.txt_output.insert(tk.END, "2. Executing: git restore --staged .\n")
        dialog.txt_output.see(tk.END)
        dialog.top.update()

        # 2. git restore --staged . (unstages changes into working directory)
        c2, out2, err2 = run_git_command("git restore --staged .", cwd=repo_dir)
        if c2 == 0:
            dialog.txt_output.insert(tk.END, "   Result: All changes successfully unstaged (edits preserved intact).\n")
        else:
            dialog.txt_output.insert(tk.END, f"   Result: {out2} {err2}\n")

        dialog.lbl_status.config(text="Commit undone and changes unstaged. Exiting in 1 second...", fg="#C62828")
        dialog.txt_output.see(tk.END)
        dialog.top.update()

        time.sleep(1.0)
        dialog.top.destroy()

    dlg3 = GitStepDialog(root, "Step 3 of 5: Committing Changes", 3, step3_cmd, on_cancel_callback=step3_cancel_handler)
    root.update()

    code3, out3, err3 = run_git_command(step3_cmd, cwd=repo_dir)
    dlg3.set_result(code3, out3, err3)
    root.wait_window(dlg3.top)

    if not dlg3.result_proceed:
        sys.exit(0)

    # -------------------------------------------------------------------------
    # STEP 4 of 5: Updating Remote Repository (git push origin -u <branch>)
    # -------------------------------------------------------------------------
    step4_cmd = f"git push origin -u {branch}"

    def step4_cancel_handler(dialog):
        """Rolls back remote repository and local commit/staging while preserving local edits intact"""
        dialog.lbl_status.config(text="Reverting remote and preserving local modifications...", fg="#C62828")
        dialog.txt_output.insert(tk.END, "\n\n[Action: Cancelled by user - Rolling back Step 4]\n")
        dialog.txt_output.insert(tk.END, "1. Executing: git reset --soft HEAD~1\n")
        dialog.txt_output.see(tk.END)
        dialog.top.update()

        # 1. git reset --soft HEAD~1
        c1, out1, err1 = run_git_command("git reset --soft HEAD~1", cwd=repo_dir)
        if c1 == 0:
            dialog.txt_output.insert(tk.END, "   Result: Local commit undone (file modifications preserved).\n")
        else:
            dialog.txt_output.insert(tk.END, f"   Result:\n   {out1}\n   {err1}\n")

        dialog.txt_output.insert(tk.END, "2. Executing: git restore --staged .\n")
        dialog.txt_output.see(tk.END)
        dialog.top.update()

        # 2. git restore --staged .
        c2, out2, err2 = run_git_command("git restore --staged .", cwd=repo_dir)
        if c2 == 0:
            dialog.txt_output.insert(tk.END, "   Result: Staging undone (files remain modified in working directory).\n")
        else:
            dialog.txt_output.insert(tk.END, f"   Result:\n   {out2}\n   {err2}\n")

        force_push_cmd = f"git push --force-with-lease origin {branch}"
        dialog.txt_output.insert(tk.END, f"3. Executing: {force_push_cmd}\n")
        dialog.txt_output.see(tk.END)
        dialog.top.update()

        # 3. git push --force-with-lease origin <branch>
        c3, out3, err3 = run_git_command(force_push_cmd, cwd=repo_dir)
        if c3 == 0:
            dialog.txt_output.insert(tk.END, "   Result: Remote repository successfully rolled back to previous build.\n")
            if out3 or err3:
                dialog.txt_output.insert(tk.END, f"   {out3}\n   {err3}\n")
        else:
            dialog.txt_output.insert(tk.END, f"   Result:\n   {out3}\n   {err3}\n")

        dialog.lbl_status.config(text="Remote rolled back, local edits preserved intact. Exiting in 1 second...", fg="#C62828")
        dialog.txt_output.see(tk.END)
        dialog.top.update()

        time.sleep(1.0)
        dialog.top.destroy()

    dlg4 = GitStepDialog(root, "Step 4 of 5: Updating Remote Repository (git push)", 4, step4_cmd, on_cancel_callback=step4_cancel_handler)
    root.update()

    code4, out4, err4 = run_git_command(step4_cmd, cwd=repo_dir)
    dlg4.set_result(code4, out4, err4)
    root.wait_window(dlg4.top)

    if not dlg4.result_proceed:
        sys.exit(0)

    # -------------------------------------------------------------------------
    # STEP 5 of 5: Final Post-Update Status (git status)
    # -------------------------------------------------------------------------
    step5_cmd = "git status"

    def step5_cancel_handler(dialog):
        """Rolls back remote repository and local commit/staging while preserving working directory edits"""
        dialog.lbl_status.config(text="Reverting remote and preserving local modifications...", fg="#C62828")
        dialog.txt_output.insert(tk.END, "\n\n[Action: Cancelled on final step - Rolling back remote & keeping local edits intact]\n")
        dialog.txt_output.insert(tk.END, "1. Executing: git reset --soft HEAD~1\n")
        dialog.txt_output.see(tk.END)
        dialog.top.update()

        # 1. git reset --soft HEAD~1
        c1, out1, err1 = run_git_command("git reset --soft HEAD~1", cwd=repo_dir)
        if c1 == 0:
            dialog.txt_output.insert(tk.END, "   Result: Local commit undone (all file modifications preserved).\n")
        else:
            dialog.txt_output.insert(tk.END, f"   Result:\n   {out1}\n   {err1}\n")

        dialog.txt_output.insert(tk.END, "2. Executing: git restore --staged .\n")
        dialog.txt_output.see(tk.END)
        dialog.top.update()

        # 2. git restore --staged .
        c2, out2, err2 = run_git_command("git restore --staged .", cwd=repo_dir)
        if c2 == 0:
            dialog.txt_output.insert(tk.END, "   Result: Staging undone (files remain modified in working directory).\n")
        else:
            dialog.txt_output.insert(tk.END, f"   Result:\n   {out2}\n   {err2}\n")

        force_push_cmd = f"git push --force-with-lease origin {branch}"
        dialog.txt_output.insert(tk.END, f"3. Executing: {force_push_cmd}\n")
        dialog.txt_output.see(tk.END)
        dialog.top.update()

        # 3. git push --force-with-lease origin <branch>
        c3, out3, err3 = run_git_command(force_push_cmd, cwd=repo_dir)
        if c3 == 0:
            dialog.txt_output.insert(tk.END, "   Result: Remote repository successfully rolled back to previous build.\n")
            if out3 or err3:
                dialog.txt_output.insert(tk.END, f"   {out3}\n   {err3}\n")
        else:
            dialog.txt_output.insert(tk.END, f"   Result:\n   {out3}\n   {err3}\n")

        dialog.lbl_status.config(text="Remote rolled back, local edits preserved intact. Exiting in 1 second...", fg="#C62828")
        dialog.txt_output.see(tk.END)
        dialog.top.update()

        time.sleep(1.0)
        dialog.top.destroy()

    dlg5 = GitStepDialog(root, "Step 5 of 5: Final Post-Update Status (git status)", 5, step5_cmd, on_cancel_callback=step5_cancel_handler)
    dlg5.btn_cancel.config(text="Cancel")
    dlg5.btn_ok.config(text="  Exit  ")
    root.update()

    code5, out5, err5 = run_git_command(step5_cmd, cwd=repo_dir)
    dlg5.set_result(code5, out5, err5)
    dlg5.btn_cancel.config(text="Cancel")
    dlg5.btn_ok.config(text="  Exit  ")
    root.wait_window(dlg5.top)


if __name__ == "__main__":
    main()
