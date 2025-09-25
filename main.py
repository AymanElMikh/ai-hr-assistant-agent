import os
import sys
from datetime import datetime
from langchain_core.messages import HumanMessage

# Import the optimized agent components
from rh_assistant_agent import app

from utils import (
    build_default_config,
    initialize_state,
    print_stage_info,
    safe_invoke_graph,
    GlobalConfig
)

# ==============================================================================
# Configuration for UI Messages and Commands
# ==============================================================================
class UIConfig:
    """Configuration for UI messages and commands to reduce hardcoded strings."""
    
    # Welcome message components
    TITLE = "AI HR Assistant for Annual Performance Reviews"
    TITLE_SEPARATOR = "=" * 64
    
    FEATURES = [
        "Professional advancements & milestones",
        "Challenges & obstacles faced", 
        "Key achievements & accomplishments",
        "Training & development needs",
        "Action plans & future goals",
        "Comprehensive review summary"
    ]
    
    TIPS = [
        "Be specific and detailed in your responses",
        "Use examples to illustrate your points",
        "Type 'help' for guidance at any stage",
        "Type 'status' to see current progress",
        "Type 'exit' or 'quit' to end the session"
    ]
    
    # Command mappings
    EXIT_COMMANDS = {'exit', 'quit', 'bye', 'stop'}
    HELP_COMMANDS = {'help', '?', 'assistance'}
    STATUS_COMMANDS = {'status', 'progress', 'where'}
    RESET_COMMANDS = {'reset', 'restart', 'start over'}
    
    # Response templates
    PROCESSING_MSG = "🤔 Processing your response..."
    ERROR_MSG = "❌ Sorry, I encountered an error: {error}"
    EMPTY_INPUT_MSG = "❓ Please enter your response or type 'help' for assistance."
    
    # File naming
    SUMMARY_FILENAME_TEMPLATE = "performance_review_summary_{timestamp}.txt"
    SUMMARY_HEADER = "ANNUAL PERFORMANCE REVIEW SUMMARY\n" + "=" * 40 + "\n\n"

# ==============================================================================
# Enhanced Main Application Class
# ==============================================================================
class HRAssistantApp:
    """
    Main application class for the HR Assistant with improved configuration management.
    """
    
    def __init__(self, global_config: GlobalConfig = None, ui_config: UIConfig = None):
        self.app = app
        self.global_config = global_config or build_default_config()
        self.ui_config = ui_config or UIConfig()
        self.config = {"configurable": {"thread_id": "hr_session"}}
        self.state = None
        
    def start(self):
        """Start the HR Assistant application."""
        self._print_welcome_message()
        self.state = initialize_state(self.global_config)
        
        # Print initial message
        initial_message = self.state["messages"][-1].content
        print(f"🤖 Assistant: {initial_message}")
        print_stage_info(self.state["current_stage"], self.global_config)
        
        self._conversation_loop()
    
    def _print_welcome_message(self):
        """Print the welcome message using configuration."""
        print(f"🎯 {self.ui_config.TITLE_SEPARATOR}")
        print(f"   {self.ui_config.TITLE}")
        print(self.ui_config.TITLE_SEPARATOR)
        print()
        
        print("📋 This assistant will guide you through:")
        for feature in self.ui_config.FEATURES:
            print(f"   • {feature}")
        print()
        
        print("💡 Tips:")
        for tip in self.ui_config.TIPS:
            print(f"   • {tip}")
        print(self.ui_config.TITLE_SEPARATOR)
        print()
    
    def _conversation_loop(self):
        """Main conversation loop with improved error handling."""
        while True:
            try:
                user_input = input("\n💬 You: ").strip()
                
                if not user_input:
                    print(self.ui_config.EMPTY_INPUT_MSG)
                    continue
                
                # Handle special commands
                if self._handle_special_commands(user_input):
                    continue
                
                # Process user input
                self._process_user_input(user_input)
                
            except KeyboardInterrupt:
                print("\n\n👋 Session interrupted. Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ An unexpected error occurred: {str(e)}")
                print("Please try again or type 'exit' to quit.")
    
    def _handle_special_commands(self, user_input: str) -> bool:
        """Handle special commands using configuration-based command sets."""
        command = user_input.lower().strip()
        
        if command in self.ui_config.EXIT_COMMANDS:
            self._exit_application()
            return True
        
        elif command in self.ui_config.HELP_COMMANDS:
            self._show_help()
            return True
        
        elif command in self.ui_config.STATUS_COMMANDS:
            self._show_status()
            return True
        
        elif command in self.ui_config.RESET_COMMANDS:
            self._reset_session()
            return True
        
        return False
    
    def _process_user_input(self, user_input: str):
        """Process user input through the LangGraph agent."""
        # Add user message to state
        self.state["messages"].append(HumanMessage(content=user_input))
        
        print(f"\n{self.ui_config.PROCESSING_MSG}")
        
        # Invoke the graph
        result, error = safe_invoke_graph(self.app, self.state, self.config)
        
        if error:
            print(self.ui_config.ERROR_MSG.format(error=error))
            print("Please try rephrasing your response.")
            return
        
        # Update state with result
        self.state.update(result)
        
        # Get and display the assistant's response
        last_message = self.state["messages"][-1]
        if hasattr(last_message, 'content') and last_message.content:
            print(f"\n🤖 Assistant: {last_message.content}")
        
        # Show stage transition if it occurred
        current_stage = self.state["current_stage"]
        next_stage = self.state.get("next_stage")
        
        if next_stage and next_stage != current_stage:
            print_stage_info(next_stage, self.global_config)
        
        # Check if we've reached the summary stage
        if current_stage == "summary":
            self._handle_summary_completion()
    
    def _handle_summary_completion(self):
        """Handle completion of the performance review."""
        print("\n✅ Performance review discussion completed!")
        print("📄 Summary has been generated above.")
        
        save_option = input("\n💾 Would you like to save this summary? (y/n): ").lower()
        if save_option == 'y':
            self._save_summary()
    
    def _show_help(self):
        """Show context-sensitive help based on current stage."""
        if not self.state:
            print("Type your response to begin the conversation.")
            return
            
        current_stage = self.state["current_stage"]
        stage_config = self.global_config.stages.get(current_stage)
        
        if not stage_config:
            print("General help: Please respond to the assistant's questions.")
            return
        
        # Get help content based on stage
        help_content = self._get_stage_help_content(current_stage)
        print(f"\n{stage_config.pretty_name} Help:")
        print(help_content)
    
    def _get_stage_help_content(self, stage: str) -> str:
        """Get help content for a specific stage."""
        help_content_map = {
            "advancements": """
   • Describe new skills you've developed
   • Mention certifications or training completed  
   • Highlight process improvements you've made
   • Share technology or tools you've mastered
   • Include leadership or mentoring experiences
            """,
            "challenges": """
   • Be honest about difficulties faced
   • Focus on learning experiences
   • Mention resource constraints or barriers
   • Include team or communication challenges
   • Describe how you approached problem-solving
            """,
            "achievements": """
   • Quantify your results with numbers/metrics
   • Include project successes and deliverables
   • Mention recognition or awards received
   • Highlight contributions to team/company goals
   • Share positive feedback from clients/colleagues
            """,
            "training_needs": """
   • Identify skill gaps you want to address
   • Mention industry trends you want to learn about
   • Include technical skills or certifications needed
   • Consider leadership or soft skills development
   • Think about career advancement requirements
            """,
            "action_plan": """
   • Set specific, measurable goals
   • Include realistic timelines
   • Identify resources or support needed
   • Plan regular check-in points
   • Consider both short-term and long-term objectives
            """
        }
        
        return help_content_map.get(stage, "Provide detailed responses with specific examples.")
    
    def _show_status(self):
        """Show current session status and progress using configuration."""
        if not self.state:
            print("📊 Session not started yet.")
            return
        
        current_stage = self.state["current_stage"]
        stage_order = self.global_config.stage_order
        
        try:
            current_idx = stage_order.index(current_stage)
        except ValueError:
            current_idx = 0
        
        print(f"\n📊 Progress Status:")
        print(f"Current Stage: {current_stage.title().replace('_', ' ')}")
        print(f"Progress: {current_idx + 1}/{len(stage_order)} stages")
        
        if current_idx > 0:
            print(f"\n✅ Completed Stages:")
            for stage in stage_order[:current_idx]:
                stage_name = self.global_config.stages.get(stage, {}).get('pretty_name', stage.title())
                print(f"   • {stage_name}")
        
        if current_idx < len(stage_order) - 1:
            print(f"\n⏭️  Upcoming Stages:")
            for stage in stage_order[current_idx + 1:]:
                stage_name = self.global_config.stages.get(stage, {}).get('pretty_name', stage.title())
                print(f"   • {stage_name}")
    
    def _reset_session(self):
        """Reset the current session with confirmation."""
        confirm = input("⚠️  Are you sure you want to reset the session? All progress will be lost. (y/n): ")
        if confirm.lower() == 'y':
            self.state = initialize_state(self.global_config)
            print("🔄 Session reset successfully!")
            print_stage_info(self.state["current_stage"], self.global_config)
    
    def _save_summary(self):
        """Save the performance review summary to a file."""
        try:
            # Find the summary content
            summary_content = self._extract_summary_content()
            
            if summary_content:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = self.ui_config.SUMMARY_FILENAME_TEMPLATE.format(timestamp=timestamp)
                
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(self.ui_config.SUMMARY_HEADER)
                    f.write(summary_content)
                
                print(f"💾 Summary saved to: {filename}")
            else:
                print("❌ Could not find summary content to save.")
                
        except Exception as e:
            print(f"❌ Error saving summary: {str(e)}")
    
    def _extract_summary_content(self) -> str:
        """Extract summary content from messages."""
        for message in reversed(self.state["messages"]):
            if hasattr(message, 'content') and message.content:
                content = message.content.lower()
                if any(keyword in content for keyword in ['summary', 'review', 'overview']):
                    return message.content
        return ""
    
    def _exit_application(self):
        """Clean exit from the application."""
        print("\n👋 Thank you for using the HR Assistant!")
        
        if self.state and self.state["current_stage"] != "summary":
            save_progress = input("💾 Would you like to save your current progress? (y/n): ").lower()
            if save_progress == 'y':
                # Future enhancement: implement progress saving
                print("💾 Progress saving feature will be available in future versions.")
        
        print("🎯 Have a great day!")
        sys.exit(0)

# ==============================================================================
# Application Factory and Entry Point
# ==============================================================================
def create_hr_app(custom_global_config: GlobalConfig = None, custom_ui_config: UIConfig = None) -> HRAssistantApp:
    """Factory function to create HR Assistant app with custom configurations."""
    return HRAssistantApp(custom_global_config, custom_ui_config)

def main():
    """Main entry point for the application with improved error handling."""
    try:
        # Validate environment before starting
        global_config = build_default_config()
        from utils import validate_environment
        validate_environment(global_config)
        
        # Create and start the application
        app = create_hr_app(global_config)
        app.start()
        
    except EnvironmentError as e:
        print(f"❌ Environment Error: {str(e)}")
        print("Please check your environment variables and try again.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Fatal error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()