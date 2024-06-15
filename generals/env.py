import functools
from copy import copy
import time

import gymnasium
from gymnasium.spaces import Discrete

import pettingzoo
from pettingzoo.utils import wrappers, agent_selector

from typing import List

from . import game, config, utils




def generals_v0(config=config.Config, render_mode="human"):
    """
    Here we apply wrappers to the environment.
    """
    env = Generals(config)
    # Apply parallel_to_aec to support AEC api
    # env = pettingzoo.utils.parallel_to_aec(env)
    return env


class Generals(pettingzoo.ParallelEnv):
    metadata = {'render.modes': ["human", "none"]}

    def __init__(self, game_config: config.Config, agent_names: List[str] = ['red', 'blue'], render_mode="human"):
        self.game_config = game_config
        self.render_mode = render_mode

        self.agents = agent_names
        self.possible_agents = self.agents[:]
        # self.num_agents = len(self.agents)
        # self.max_num_agents = len(self.agents)
        self.agent_names = agent_names

        self.name_to_id = dict(zip(self.agent_names, list(range(1, len(self.agent_names)+1))))

        if render_mode == "human":
            utils.init_screen(self.game_config)

    @functools.lru_cache(maxsize=None)
    def observation_space(self, agent_name):
        assert agent_name in self.agent_names, f"{agent_name} is not a valid agent"
        return self.game.observation_space

    @functools.lru_cache(maxsize=None)
    def action_space(self, agent_name):
        assert agent_name in self.agent_names, f"{agent_name} is not a valid agent"
        return self.game.action_space

    def render(self):
        if self.render_mode == "human":
            utils.handle_events()
            utils.render_grid(self.game, [1, 2])
            utils.render_gui(self.game, self.agents)
            utils.pygame.display.flip()
            time.sleep(0.1) # this is digsuting, fix it later (?)

    def reset(self, seed=None, options=None):
        self.game = game.Game(self.game_config)
        self.agents = copy(self.possible_agents)

        observations = {
            agent: self.game.agent_observation(self.name_to_id[agent]) for agent in self.agents
        }
        infos = {agent: {} for agent in self.agents}
        return observations, infos


    def step(self, actions):
        actions = {self.name_to_id[k]: v for k, v in actions.items()}
        observations, rewards, terminated, truncated, infos = self.game.step(actions)
        # maybe some postprocessing here
        return observations, rewards, terminated, truncated, infos

    def close(self):
        utils.pygame.quit()

