print("Starting the script...")

from agents.web_agent import WebAutomationAgent

print("Imported WebAutomationAgent successfully")

if __name__ == "__main__":
    print("Entering main block")
    agent = WebAutomationAgent()
    print("Agent initialized")

    while True:
        url = input("\nEnter the website URL to open (or type 'exit' to quit): ").strip().lower()

        if url in ["exit", "quit"]:
            print("Closing browser and exiting the program...")
            agent.browser.cleanup()  # Close the browser before exiting
            break
        new_tab = "new tab" in url
        url = url.replace("new tab", "").strip()
        # print(f"URL entered: {url} (New Tab: {new_tab})")
        # agent.browser.open_website(url, new_tab=new_tab)  # Pass new_tab flag

        print(f"URL entered: {url}")
        result = agent.run(url)
        print("\nTest Result:", result)

        # Ask user if they want to close the browser
        close_browser = input("\nDo you want to close the browser? (yes/no): ").strip().lower()
        if close_browser in ["yes", "y"]:
            agent.browser.cleanup()
            print("Browser closed.")
            break  # Exit after closing browser
