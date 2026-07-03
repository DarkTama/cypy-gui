# cypy/core/theme.py
# ✦ Premium CLI Theme and Console Grid Formatter for CYPY ✦

import os

class Colors:
    """ANSI color codes for premium terminal formatting."""
    PURPLE = "\033[95m"
    CYAN = "\033[96m"
    BLUE = "\033[94m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    RESET = "\033[0m"

def print_logo(version):
    """Prints the CYPY logo and startup message."""
    print(f"\n{Colors.CYAN}{Colors.BOLD}┌────────────────────────────────────────┐")
    print(f"│      CYPY v{version:<7} - Manga Translator     │")
    print(f"│      Ready to translate~ (◠‿●) ~♪       │")
    print(f"└────────────────────────────────────────┘{Colors.RESET}")

def print_box(title, options, col_width=28):
    """
    Dynamically prints a list of options in a compact 2-column grid layout inside an ASCII box.
    """
    # Calculate rows needed for 2 columns
    num_items = len(options)
    half = (num_items + 1) // 2
    
    # Calculate layout widths
    box_width = (col_width * 2) + 3 # 2 columns + divider + padding margins
    
    # Border printing
    print(f"\n{Colors.PURPLE}┌{'─' * box_width}┐")
    
    # Title line
    padded_title = f"  {title:<{box_width - 2}}"
    print(f"│{Colors.BOLD}{Colors.CYAN}{padded_title}{Colors.PURPLE}│")
    print(f"├{'─' * box_width}┤")
    
    # Options grid
    for i in range(half):
        col1 = options[i]
        col2 = options[i + half] if (i + half) < num_items else ""
        
        # Format columns with fixed widths
        col1_str = f" {col1:<{col_width}}"
        col2_str = f" {col2:<{col_width}}"
        
        print(f"│{Colors.RESET}{col1_str}│{col2_str}{Colors.PURPLE}│")
        
    print(f"└{'─' * box_width}┘{Colors.RESET}")

def tampilkan_status(provider, target_language):
    """Prints the currently active configuration status."""
    print(f"\n{Colors.GREEN}{Colors.BOLD}[+] Current Configuration:{Colors.RESET}")
    print(f"  {Colors.BOLD}Provider{Colors.RESET} : {provider.provider_name}")
    print(f"  {Colors.BOLD}Model{Colors.RESET}    : {provider.model_name}")
    if hasattr(provider, "base_url") and provider.base_url:
        print(f"  {Colors.BOLD}Base URL{Colors.RESET} : {provider.base_url}")
    print(f"  {Colors.BOLD}Language{Colors.RESET} : {target_language}")

def tampilkan_help():
    """Prints help menu options in a 2-column grid."""
    print(f"\n{Colors.CYAN}{Colors.BOLD}┌────────────────────────────────────────────────────────┐")
    print(f"│  Available CLI Commands:                               │")
    print(f"├────────────────────────────────────────────────────────┤")
    print(f"│  [drag file]   : Translate image, PDF or Archive       │")
    print(f"│  [drag folder] : Batch translate all images in folder  │")
    print(f"│  lang / switch : Change target language                │")
    print(f"│  provider / api: Switch API provider                   │")
    print(f"│  model         : Change the LLM model name             │")
    print(f"│  status        : Show current settings                 │")
    print(f"│  tweak         : Adjust layout & filter parameters     │")
    print(f"│  help          : Show this help menu                   │")
    print(f"│  stop / exit   : Exit cypy CLI                         │")
    print(f"└────────────────────────────────────────────────────────┘{Colors.RESET}")
