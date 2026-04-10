import sys


def main() -> None:
    if len(sys.argv) > 1:
        from transform_data.transform import main as cli_main
        cli_main()
    else:
        try:
            import tkinter  # noqa: F401
        except ImportError:
            print(
                "tkinter ist in dieser Python-Umgebung nicht verfügbar.\n"
                "Bitte CLI verwenden:\n"
                "  python -m transform_data.transform <json_datei> <workflow_datei>",
                file=sys.stderr,
            )
            sys.exit(1)
        from transform_data.gui import TransformApp
        TransformApp().mainloop()


if __name__ == "__main__":
    main()
