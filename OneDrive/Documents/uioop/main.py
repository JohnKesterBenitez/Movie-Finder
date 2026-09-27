def main() -> None:
    try:
        from k3_rms.app import run

        run()


    except Exception as exc:
        print(f"Application failed to start: {exc}")


if __name__ == "__main__":
    main()
 