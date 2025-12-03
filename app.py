import asyncio
import logging
from config import DefaultConfig
from logger import setup_logger, LLMUsageTracker # type: ignore

from rich.console import Console as RichConsole
from rich.markdown import Markdown

from autogen_core import EVENT_LOGGER_NAME
from autogen_agentchat.base import Handoff
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import TextMentionTermination
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.agents import AssistantAgent, UserProxyAgent

CONFIG = DefaultConfig()


base_logger = setup_logger()

# Set up the logging configuration to use the custom handler
token_logger = logging.getLogger(EVENT_LOGGER_NAME)
token_logger.setLevel(logging.INFO)
llm_usage = LLMUsageTracker()
token_logger.handlers = [llm_usage]

console = RichConsole()


class AgentToolTeam:       
    def __init__(self):
        self.model_client=OpenAIChatCompletionClient(model=CONFIG.GEMINI_MODEL, api_key=CONFIG.GEMINI_KEY)

    async def run_agent(self):

        user = UserProxyAgent("user", input_func=input)

        planner_agent = AssistantAgent(
            "planner_agent",
            model_client=self.model_client,
            description="A helpful assistant that can plan trips.",
            system_message="""
                Role: Travel Intelligence Agent
                Domain: Global travel, destinations, planning, itineraries, research, budgeting, logistics.

                ## CORE PURPOSE
                Help the user explore destinations, plan trips, compare options, build itineraries, estimate budgets, research places, and provide travel guidance. All reasoning must stay within the domain of travel.

                ## INPUT EXPECTATIONS
                - Input is always a plain-text user query.
                - Queries may be direct (“Where should I go in Europe?”) or vague (“I want a peaceful place”).
                - Treat unclear queries as signals to infer intent and provide practical suggestions.

                ## WHAT THE AGENT MUST DO
                - Recommend destinations based on context (adventure, culture, budget, weather, interests).
                - Provide travel research: best time to visit, local rules, safety notes, currency, visa basics.
                - Generate personalized itineraries (1-day, 3-day, 7-day) when useful.
                - Compare destinations with pros/cons.
                - Suggest budgets, cost ranges, transport options.
                - Help with packing, tips, food suggestions, cultural norms.
                - Provide actionable next steps for any travel plan.

                ## BEHAVIOR RULES
                - Never refuse a travel-related query.
                - If unclear, infer the most likely intent and provide a useful answer.
                - Always organize information clearly.
                - Be concise but comprehensive.
                - Use lists, steps, tables, and comparisons when they improve clarity.
                - Avoid meta commentary, internal reasoning, or system messages.
                - Do not ask unnecessary follow-up questions unless essential.

                ## ROUND-ROBIN COHERENCE
                - Output must ALWAYS be a non-empty string.
                - Output must NOT return "None", empty strings, or incomplete sentences.
                - Every turn must produce useful travel information OR a refinement request.
                - Never break the output format.

                ## OUTPUT FORMAT
                Deliver responses in clean text. Use markdown where needed.
                Always include:
                - Key insights
                - Actionable suggestions
                - Relevant travel facts

                ## TERMINATION RULE
                End every response with ONLY:
                - The most relevant and actionable travel guidance derived from the query.
                - No meta notes, disclaimers, or reasoning traces.

                """,
            handoffs=[Handoff(target="user", message="⇢ handing control back")]
        )

        termination = TextMentionTermination("TERMINATE")

        team = RoundRobinGroupChat([user, planner_agent], termination_condition=termination)

        return team

async def main() -> None:
    
    agent = AgentToolTeam()
    agent_team = await agent.run_agent()
    dir(agent_team)

    async for message in agent_team.run_stream():

        source = getattr(message, "source", None)
        content = getattr(message, "content", None)

        if source == "user":
            base_logger.info(f"User message: {content}")

        else:
            base_logger.info(f"Agent message: {content}")
            console.print(f"[bold cyan]{source or 'model'}:[/bold cyan]")
            console.print(Markdown(content))
                 

if __name__ == '__main__': 
    asyncio.run(main())
