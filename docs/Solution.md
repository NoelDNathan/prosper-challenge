

# Table of Contents

- [Table of Contents](#table-of-contents)
- [Project Structure (summary)](#project-structure-summary)
- [1. Overview](#1-overview)
- [2. Conversation Flow](#2-conversation-flow)
- [3. Installation](#3-installation)
- [4. Healthie Integration](#4-healthie-integration)
  - [Adapters](#adapters)
  - [Live Healthie Tests](#live-healthie-tests)
- [5.Potential Improvements](#5potential-improvements)
- [6. Future Considerations](#6-future-considerations)
- [7. Example Conversation](#7-example-conversation)
  - [Conclusion](#conclusion)

#  Project Structure (summary)

- `/integration`: Playwright flows that interact with Healthie’s web UI.
- `/adapters/pipecat`: Glue code that exposes the integration functions to the Pipecat bot.
- `/utils`: Shared helpers such as `get_verification_code` and `date_helpers`.
- `/tests`: PyTest suites (including `test_healthie_live.py`) that drive live integrations.
- `/docs`: Documentation artifacts describing the conversation flow and testing commands.

# 1. Overview

The agent first asks the user for a name and birthdate through a dialog. Once those details are available, it searches for an existing patient. If the patient is found, the agent offers to create an appointment. When the user confirms, the bot asks for a date and time and then schedules the appointment with the gathered information.

# 2. Conversation Flow

- **Question order**: name → birthdate → appointment date and time.
- **Error handling**: If any step returns incomplete or missing data, the bot repeats the question or requests clarification before advancing.
- **Function calling**: We chose direct functions rather than Pipecat function calling for this flow. It keeps the logic in one place while we iterate rapidly on the pipeline.

```mermaid
flowchart TD
   A[Start] --> B[Ask Name and Birthdate]

B --> C{Is name valid and birthdate valid?}
C -- No --> B
C -- Yes --> D[Call find_patient]

D --> E{Success?}
E -- No --> B
E -- Yes --> F[Ask Appointment Date and Time]

F --> G{Is date/time valid?}
G -- No --> F
G -- Yes --> H[Call create_appointment]

H --> I{Success?}
I -- No --> F
I -- Yes --> K[Confirmation to User]

K --> L[End]
```

# 3. Installation

At the beginning, I ran into installation issues. I was unable to install the Python libraries because not all of them were compatible with Windows.

I then tried using the Docker setup you provided, but it also failed, as I continued encountering Windows related issues. After that, I attempted to use Docker with a Linux configuration. Although the installation completed successfully, the application did not run correctly.

Finally, I switched to WSL, and that approach worked without issues.

# 4. Healthie Integration

I began by using the browser inspector to identify the HTML elements Playwright needed to interact with. Prompting an LLM helped clarify how to call those elements. Later I discovered `playwright codegen https://secure.gethealthie.com`, which records actions in a browser session and shows the corresponding Playwright commands, significantly speeding up development.

1. `login_to_healthie` already existed in the base repository, so I tried to modify it as little as possible.
Healthie updated the login flow on 2026-02-18, sending a verification code to Gmail. To handle this, I added a `get_otp function` in `utils/get_verification_code` to read the code from Gmail.
They updated the flow again on 2026-02-20, removing the verification code step, but I still adjusted the login routine from the original UI version to accommodate the changes.

2. For `find_patient`, I chose to search within the Clients section rather than the main search bar because the results there listed matching users and counts more clearly. That makes it easier to detect when no matches are found or when clarification is needed. I also capture slightly more user's details than strictly necessary in case the function is reused in other scenarios.

3. `create_appointment` uses default values when possible to keep the flow simple. When multiple consultancy options exist, I picked one and left room to make that choice dynamic in a future improvement. Date handling helpers include:

   -  `convert_to_date_time(str_value)` is used to create a `datetime` object from a string, making it easier to manipulate dates and times programmatically.

   - `format_target_date(date_str, time_str)` formats the date and time strings so that they match the calendar selector in the UI. 
   - `format_appointment_label(datetime_value)` adapts the `datetime` object to the UI’s label format. This formatted label is then used to find the appointment in the list



After creating an appointment, the client section is inspected to verify that the appointment was created and extract the meeting link (and other fields if needed).

## Adapters

I created an adapter so the bot can call the integration functions directly. I preferred direct functions to the Standard Function Schema because they were faster to adjust while iterating, particularly when tweaking descriptions or formats. The adapters currently wrap `None` returns, but they would benefit from richer error information to surface more helpful messages to the user.

## Live Healthie Tests

Run the live Healthie test suite with:

```bash
uv run python -m pytest -s -vv -m live tests/test_healthie_live.py::test_create_appointment_success -o log_cli=true -o log_cli_level=INF
```
The `live` marker ensures these tests run only when explicitly requested. They require real Healthie credentials, so make sure to populate `HEALTHIE_EMAIL` and `HEALTHIE_PASSWORD` in your local `.env` file (never commit this file with secrets). The tests will automatically skip if the variables are missing and fail fast if the account cannot authenticate. These tests act as short sanity checks to confirm that the real web experience still works. Note that some tests may pass once but fail on subsequent runs unless you clean up previously created state—for example, creating the same appointment twice will fail because Healthie disallows duplicate dates.

While unit tests could be added with mocks, they risk passing even when the real UI changes. Helpers such as `utils/get_verification_code.py` are better candidates for isolated testing. In general, utility functions are the most valuable targets for unit coverage. This is why integration tests have been created for the flows that involve real interactions.

# 5.Potential Improvements

- **Latency**: A hypothetical Healthie API would reduce latency (though that is outside our control). Consolidating `find_patient` and `create_appointment` into a single login sequence could eliminate redundant steps or even unify the two flows when reusability is less critical. Playwright selectors could be optimized for speed, and shorter prompts could speed up the bot conversation. A faster bot voice might also improve the perceived responsiveness.
- **Reliability**: Add retry logic or adopt a `Result<Ok, Error>` pattern (see https://pypi.org/project/result/) so each integration function returns a structured error rather than `None`. Knowing the error type allows the bot to decide the next action (e.g., re-ask for missing fields or suggest alternative slots). Apply this pattern to `integration/healthie.py` for both `find_patient` and `create_appointment`, and propagate the richer errors through `adapters/pipecat/healthie.py` so the bot can explain issues such as occupied slots. Including a simplified real-world example in the docs would help illustrate how this flow behaves. Additionally, integrate Playwright with more robust selectors and reusable helper functions for both patient search and appointment creation flows to reduce test flakiness and improve end to end stability.
- **Evaluation**: The prompt already asks users to verify data before creating an appointment, which reduces input errors. `create_appointment` confirms that the appointment was created and returns `None` when it fails. Healthie also sends emails, so we could add a follow-up message telling users to reach out if they do not receive the confirmation email.

# 6. Future Considerations

- **Patient Disambiguation**: `find_patient` currently selects the first matching row when multiple users share the same name. Implementing stronger disambiguation, such as confirming the birthdate or requesting another identifier, would improve accuracy.

- **Multiple Appointment Types**: Extend `create_appointment` to support various appointment types dynamically, rather than relying on default values. This could make the bot more flexible for different use cases.

- **Error Handling**: Enhance functions and adapters to return explicit, structured error messages instead of `None`. This allows the bot to respond more informatively, e.g., indicating when a slot is already taken or a patient cannot be found.

- **Bot End-to-End Tests**: Add automated end-to-end tests for the bot to verify full conversation flows, including patient search and appointment creation. This ensures the bot behaves correctly as the interface or underlying logic evolves.

- **Extending Appointment Options**: Allow dynamic selection of consultancy options, locations, or other appointment attributes based on user input, rather than hardcoded defaults.

- **State Cleanup Between Tests**: Implement routines to reset user state or appointment data between test runs. This prevents live tests from failing due to leftover state (e.g., duplicate appointments).

- **Analytics and Monitoring**: Collect metrics on usage patterns, error rates, and response times. This information can guide improvements in reliability, latency, and user experience.

# 7. Example Conversation

**Assistant [23:04:16]**  
Hello! I’m your digital assistant from Prosper Health Clinic. To help you with your appointment or any health-related questions, could you please provide your full name and date of birth? This will allow me to look up your record in our Healthie system. Thank you!

**User [23:04:34]**  
My name is Noel Nathan. planeja

**Assistant [23:04:41]**  
Thank you, Noel! To make sure I find the correct record in Healthie, could you please provide your full date of birth as well?

**User [23:04:42]**  
My last name has a double L at the end.

**Assistant [23:04:46]**  
Thank you for clarifying! To make sure I have your details correct, could you please confirm your full name and also provide your date of birth? This will help me find your record accurately in Healthie.

**User [23:04:47]**  
So what's my name? Can you answer?

**Assistant [23:05:05]**  
Yes, I can answer! Based on what you’ve shared, your full name is Noel Nathan Planell. Could you please confirm if this is correct? Also, could you provide your date of birth so I can look up your record in Healthie? Thank you!

**User [23:05:15]**  
Yes. This is correct. And additionally, I have an additional last name, which is "Bosque," which is the name of the restaurant.

**Assistant [23:05:30]**  
Thank you for letting me know! So your full name is Noel Nathan Planell Bosque, correct? To help me find your record in Healthie, could you also provide your date of birth?

**User [23:05:43]**  
No, my name is not correct. The last -- both busk, shoe, and with a C. 8.

**Assistant [23:05:54]**  
Thank you for clarifying! It sounds like there might have been a misunderstanding about the spelling of your last name. Could you please type your full name exactly as it appears officially, along with your date of birth? That way, I can accurately look up your record in Healthie.

**User [23:06:04]**  
Yes, it should be C. And H. Can you confirm what you understood

**Assistant [23:06:09]**  
Thank you for clarifying! Could you please confirm the full spelling of your last name for me? That way, I can make sure I have your name exactly right before looking up your record in Healthie. Also, could you provide your date of birth? This will help me find your information quickly and accurately. Thank you for your patience!  

Here’s what I’ve understood so far:  
- Your full name is Noel Nathan Planell Bosch.  
- The last name "Bosch" is spelled with a "C" and an "H" at the end.  

Is this correct? If so, could you please also provide your date of birth so I can look up your record in Healthie?

**User [23:06:28]**  
Yes, you are right. My birthday is-- is August 28, 2003.

**Assistant [23:07:35]**  
Thank you, Noel Nathan Planell Bosch, and Happy (early or belated) Birthday for August 28, 2003! I’ve found your record in Healthie. To book your appointment, could you please let me know the date and time you’d prefer?

**User [23:07:54]**  
I would prefer an appointment on March 25, 2026.

**Assistant [23:08:09]**  
Great, thank you! What time on March 25, 2026 would you like your appointment? If you have a specific time in mind (morning or afternoon, or even an exact hour), just let me know!

**User [23:08:24]**  
11:00 AM.

**Assistant [23:08:30]**  
Your appointment is scheduled for March 25, 2026, at 11:00 AM. It will be an Initial Consultation (60 minutes) via video call. You’ll join using this link: https://secure.gethealthie.com//appointments/744774123/video_chat  

If you have any other preferences or questions, just let me know!

## Conclusion
There are still many aspects to refine to make the conversation smoother. I’m not sure if it’s my pronunciation or the fact that the names are in Spanish, but I didn’t always fully understand them. It’s also true that sometimes it thinks I’m speaking when I’m not, and the conversation gets cut off.