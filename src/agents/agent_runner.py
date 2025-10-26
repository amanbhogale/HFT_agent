                   
"""
Module for agent functions and orchestrations in LangGraph.
Contains functions and classes to define nodes, tools, and workflow logic for the agent.
"""

from src.state import State
from src.agents.tools import gemini_chat_tool, fetch_fundamentals, calculate_ratios, analyze_news_sentiment

def run_chatbot():
    """Run the interactive chatbot interface."""
    state: State = {"messages": []}
    print("Gemini Chatbot (type 'exit' to quit)")

    while True:
        try:
            user_input = input("You: ")
            if user_input.lower() == "exit":
                break

            # Ensure messages list exists
            if "messages" not in state:
                state["messages"] = []

            state["messages"].append(user_input)

            if user_input.startswith("fundamental:"):
                symbol = user_input.split("fundamental:", 1)[1].strip()
                if not symbol:
                    print("Please provide a valid symbol after 'fundamental:'")
                    continue

                print(f"Analyzing fundamentals for {symbol}...")

                # Fetch fundamentals with error handling
                try:
                    fundamentals_df = fetch_fundamentals(symbol)
                    if not fundamentals_df.empty:
                        print("Fundamentals fetched successfully:")
                        print(fundamentals_df.head())
                        print("Columns:", fundamentals_df.columns.tolist())
                    else:
                        print("No fundamental data found for this symbol")
                        continue
                except Exception as e:
                    print(f"Error fetching fundamentals: {e}")
                    continue

                # Calculate ratios with error handling
                try:
                    ratios_df = calculate_ratios(fundamentals_df)
                    if not ratios_df.empty:
                        print("Ratios calculated successfully:")
                        print(ratios_df.head())
                    else:
                        print("Could not calculate ratios")
                        ratios_df = None
                except Exception as e:
                    print(f"Error calculating ratios: {e}")
                    ratios_df = None

                # Simple news placeholder
                sample_news = [
                    {
                        "headline": f"{symbol} quarterly report released", 
                        "summary": "Strong financial performance."
                    }
                ]

                # Analyze sentiment with error handling
                try:
                    sentiments = analyze_news_sentiment(sample_news)
                    print(f"Sentiment analysis completed for {len(sentiments)} articles")
                except Exception as e:
                    print(f"Error in sentiment analysis: {e}")
                    sentiments = []

                # Store fundamental data
                try:
                    state["fundamental_data"] = {
                        "symbol": symbol,
                        "fundamentals": fundamentals_df.to_dict(orient="records") if fundamentals_df is not None and not fundamentals_df.empty else [],
                        "ratios": ratios_df.to_dict(orient="records") if ratios_df is not None and not ratios_df.empty else []
                    }
                except Exception as e:
                    print(f"Error converting fundamentals or ratios to dict: {e}")
                    state["fundamental_data"] = {
                        "symbol": symbol,
                        "fundamentals": [],
                        "ratios": []
                    }

                # Store sentiment data
                try:
                    state["sentiment_data"] = sentiments
                except Exception as e:
                    print(f"Error setting sentiment data: {e}")
                    state["sentiment_data"] = []

                # Create summary message
                try:
                    if ratios_df is not None and not ratios_df.empty:
                        if "EPS" in ratios_df.columns and "P/E" in ratios_df.columns:
                            eps = ratios_df['EPS'].iloc[0]
                            pe_ratio = ratios_df['P/E'].iloc[0]
                            msg = f"Fundamental analysis for {symbol} complete. EPS: {eps:.2f}, P/E: {pe_ratio:.2f}"
                        else:
                            msg = f"Fundamental analysis for {symbol} complete, but some ratio data is missing."
                    else:
                        msg = f"Fundamental analysis for {symbol} completed with limited data."

                    state["messages"].append(msg)
                    print(f"Analysis Summary: {msg}")
                except Exception as e:
                    print(f"Error creating summary message: {e}")

            # Process with Gemini chat tool
            try:
                state = gemini_chat_tool(state)
                if state["messages"]:
                    print("Bot:", state["messages"][-1])
                else:
                    print("Bot: No response generated")
            except Exception as e:
                print(f"Error in gemini_chat_tool: {e}")
                print("Bot: Sorry, I encountered an error processing your request.")

        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"Unexpected error: {e}")
            print("Continuing...")

if __name__ == "__main__":
    run_chatbot()

