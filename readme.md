Project Brief: AI HR Assistant for Annual Performance Reviews
This document outlines the scope, objectives, and key functionalities for an AI assistant designed to facilitate and enhance yearly performance review interviews between an employee and a manager. The assistant will act as a structured guide and a data capture tool to ensure consistency and effectiveness across all reviews.

1. Objectives
The primary objective of the AI HR Assistant is to:

Automate and standardize the performance review process.

Enhance the quality of discussions by ensuring all key topics are covered.

Empower employees to reflect on their past performance and future ambitions.

Align individual development with the company’s long-term strategy.

Generate a clear, actionable summary of the interview.

2. Core Functions & Discussion Points
The assistant will guide the conversation through the following structured points, ensuring a comprehensive review.

Employee's Progress & Performance
Advancements: Discuss and document significant progress and milestones achieved since the last review.

Challenges: Identify and analyze the main challenges and obstacles encountered.

Achievements: Highlight key successes and positive contributions to the team and company.

Professional Development & Needs
Formations & Training: Pinpoint specific training, workshops, or educational resources the employee needs to acquire new skills or improve existing ones.

Resources & Support: Discuss any additional tools, mentorship, or support required to perform their role more effectively.

Future Goals & Strategic Alignment
Plan of Actions: Co-create a concrete, time-bound action plan with clear goals for the upcoming year.

Alignment: Ensure the employee’s personal and professional goals are aligned with the company’s long-term strategies and objectives.

3. Required Data & Inputs
To function effectively, the assistant will need access to the following data points:

Employee Data: Basic information, role, department, and date of last review.

Past Performance Data: Previous review summaries, goals, and any performance metrics.

Company Strategy: Access to documentation outlining the company’s long-term vision, quarterly objectives, and key results (OKRs).

4. Expected Outputs & Reporting
Upon completion of the interview, the assistant will generate a structured and easy-to-read report. This report should include:

A concise summary of the discussion.

The agreed-upon action plan with clear responsibilities and deadlines.

A list of identified training needs and next steps.

A section for follow-up notes for both the employee and the manager.

5. Technology Stack & Architecture
The assistant will be built using LangChain and LangGraph, following a multi-step agent architecture. This approach allows for a flexible and stateful conversation flow, ensuring that the assistant can adapt to the employee's input while maintaining the structured flow of the interview.

Tools: New tools will be developed to handle database interactions (e.g., retrieving employee data, saving action plans) and to generate the final report.

State Management: The LangGraph state will be expanded to track the progress of the interview, current topic, and key information captured during the discussion.

LLM: An advanced LLM (e.g., GPT-4o) will be used for natural language understanding and conversation generation.

6. Development & Deployment Phases
Phase 1: Tool & Functionality Development: Build and test the new tools and the core conversation flow.

Phase 2: Data Integration: Connect the agent to a database (e.g., Firebase Firestore) to handle persistent storage of review data.

Phase 3: User Interface & Reporting: Develop a simple user interface for the manager and employee to interact with the assistant and view the generated reports.
