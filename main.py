import os
from rich.console import Console
from rich.prompt import Prompt
from extractors import parse_source_doc, parse_email_text
from generators import generate_word_docs

console = Console()

def main():
    console.print("[bold green]Document Streamlining Tool[/bold green]")

    # 1. Setup Paths
    base_dir = os.path.dirname(os.path.abspath(__file__))
    inputs_dir = os.path.join(base_dir, "inputs")
    outputs_dir = os.path.join(base_dir, "outputs")
    templates_dir = os.path.join(base_dir, "docx_templates")

    # 2. Check Input File
    # Find the first .docx in inputs
    input_files = [f for f in os.listdir(inputs_dir) if f.endswith('.docx')]
    if not input_files:
        console.print("[bold red]No .docx found in inputs text![/bold red]")
        return

    source_path = os.path.join(inputs_dir, input_files[0])
    console.print(f"Reading source: [cyan]{input_files[0]}[/cyan]")

    # 3. Parse Source Doc
    data = parse_source_doc(source_path)
    console.print(f"Extracted {len(data)} items from Word doc.")

    # 4. Get Email Inputs via Paste (CLI)
    console.print("\n[bold yellow]--- Email 1 Input (Music Director) ---[/bold yellow]")
    console.print("Please copy the email content and paste it here. Press Enter, then Ctrl+Z (Windows) or Ctrl+D (Linux/Mac) and Enter to finish.")

    # Read multi-line input
    email_1_lines = []
    try:
        while True:
            line = input()
            email_1_lines.append(line)
    except EOFError:
        pass
    email_1_text = "\n".join(email_1_lines)

    console.print("\n[bold yellow]--- Email 2 Input (Choir/Response) ---[/bold yellow]")
    console.print("Please copy the email content and paste it here. Press Enter, then Ctrl+Z/Ctrl+D and Enter to finish.")

    email_2_lines = []
    try:
        while True:
            line = input()
            email_2_lines.append(line)
    except EOFError:
        pass
    email_2_text = "\n".join(email_2_lines)

    # 5. Parse Emails
    music_data_1 = parse_email_text(email_1_text, source_type="music_1")
    music_data_2 = parse_email_text(email_2_text, source_type="music_2")

    # Merge Data
    data.update(music_data_1)
    data.update(music_data_2)

    # 6. Generate Outputs
    console.print("\n[bold blue]Generating Documents...[/bold blue]")
    generate_word_docs(data, templates_dir, outputs_dir)

    console.print("[bold green]Done![/bold green]")

if __name__ == "__main__":
    main()
