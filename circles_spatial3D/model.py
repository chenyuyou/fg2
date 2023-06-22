#! /usr/bin/env python3
from pyflamegpu import *
from numpy import cbrt, floor
import random, time, math, sys
from cuda import *





def create_model():
    model = pyflamegpu.ModelDescription("Circles Spatial3D")
    return model

def define_environment(model):
    """
        环境设置
    """
    env = model.Environment()
#   代理个数
    env.newPropertyUInt("AGENT_COUNT", 16384)
#   环境界限
    env.newPropertyFloat("ENV_MAX", floor(cbrt(env.getPropertyUInt("AGENT_COUNT"))))
    env.newPropertyFloat("RADIUS", 2.0)
#
    env.newPropertyFloat("repulse", 0.05)
    return env

def define_messages(model, env):
#   建立一个3D信息“location”，用于管理代理的位置信息
    message = model.newMessageSpatial3D("location")
    message.newVariableID("id")
    message.setRadius(env.getPropertyFloat("RADIUS"))
    message.setMin(0, 0, 0)
    message.setMax(env.getPropertyFloat("ENV_MAX"), env.getPropertyFloat("ENV_MAX"), env.getPropertyFloat("ENV_MAX"))

def define_agents(model):
    agent = model.newAgent("Circle")
    agent.newVariableFloat("x")
    agent.newVariableFloat("y")
    agent.newVariableFloat("z")
    agent.newVariableFloat("drift")
    fn = agent.newRTCFunction("output_message", output_message)
    fn.setMessageOutput("location")
    fn = agent.newRTCFunction("move", move)
    fn.setMessageInput("location")


def define_execution_order(model):
# Layer #1
    layer = model.newLayer()
    layer.addAgentFunction("Circle", "output_message")
# Layer #2
    layer = model.newLayer()
    layer.addAgentFunction("Circle", "move")


def initialise_simulation(seed):
    model = create_model()
    env = define_environment(model)
    define_messages(model, env)
    define_agents(model)
    define_execution_order(model)

    cudaSimulation = pyflamegpu.CUDASimulation(model)

    if seed is not None:
        cudaSimulation.SimulationConfig().random_seed = seed
        cudaSimulation.applyConfig()

    if pyflamegpu.VISUALISATION:
        m_vis = cudaSimulation.getVisualisation()
    
        INIT_CAM = env.getPropertyFloat("ENV_MAX") * 1.25
        m_vis.setInitialCameraLocation(INIT_CAM, INIT_CAM, INIT_CAM)
        m_vis.setCameraSpeed(0.001)
        circ_agt = m_vis.addAgent("Circle")
    # Position vars are named x, y, z; so they are used by default
        circ_agt.setModel(pyflamegpu.ICOSPHERE)
        circ_agt.setModelScale(1/10.0)
        ENV_MIN = 0
        DIM = int(math.ceil((env.getPropertyFloat("ENV_MAX") - ENV_MIN) / env.getPropertyFloat("RADIUS")))
        DIM_MAX = DIM * env.getPropertyFloat("RADIUS")
        pen = m_vis.newLineSketch(1, 1, 1, 0.2)
        for y in range(DIM+1):
            for z in range(DIM+1):
                pen.addVertex(ENV_MIN, y * env.getPropertyFloat("RADIUS"), z *  env.getPropertyFloat("RADIUS"))
                pen.addVertex(DIM_MAX, y * env.getPropertyFloat("RADIUS"), z * env.getPropertyFloat("RADIUS"))
        for x in range(DIM+1):
            for z in range(DIM+1):
                pen.addVertex(x * env.getPropertyFloat("RADIUS"), ENV_MIN, z * env.getPropertyFloat("RADIUS"))
                pen.addVertex(x * env.getPropertyFloat("RADIUS"), DIM_MAX, z * env.getPropertyFloat("RADIUS"))
        for x in range(DIM+1):
            for y in range(DIM+1):
                pen.addVertex(x * env.getPropertyFloat("RADIUS"), y * env.getPropertyFloat("RADIUS"), ENV_MIN)
                pen.addVertex(x * env.getPropertyFloat("RADIUS"), y * env.getPropertyFloat("RADIUS"), DIM_MAX)    
        m_vis.activate()
    cudaSimulation.initialise(sys.argv)

# If no xml model file was is provided, generate a population.
    if not cudaSimulation.SimulationConfig().input_file:
    # Uniformly distribute agents within space, with uniformly distributed initial velocity.
        random.seed(cudaSimulation.SimulationConfig().random_seed)
        population = pyflamegpu.AgentVector(model.Agent("Circle"), env.getPropertyUInt("AGENT_COUNT"))
        for i in range(env.getPropertyUInt("AGENT_COUNT")):
            instance = population[i]

            instance.setVariableFloat("x",  random.uniform(0.0, env.getPropertyFloat("ENV_MAX")))
            instance.setVariableFloat("y",  random.uniform(0.0, env.getPropertyFloat("ENV_MAX")))
            instance.setVariableFloat("z",  random.uniform(0.0, env.getPropertyFloat("ENV_MAX")))

        cudaSimulation.setPopulationData(population)

    cudaSimulation.simulate()
#    cudaSimulation.exportData("end.xml")


    if pyflamegpu.VISUALISATION:
        m_vis.join()

# Ensure profiling / memcheck work correctly

if __name__ == "__main__":
    start=time.time()
    initialise_simulation(64)
    end=time.time()
    print(end-start)
    exit()

class create_agents(pyflamegpu.HostFunction):
    def run(self, FLAMEGPU):
        # Fetch the desired agent count and environment width
        AGENT_COUNT = FLAMEGPU.environment.getPropertyUInt("AGENT_COUNT")
        ENV_WIDTH = FLAMEGPU.environment.getPropertyFloat("ENV_WIDTH")
        # Create agents
        t_pop = FLAMEGPU.agent("point")
        for i in range(AGENT_COUNT):
            t = t_pop.newAgent()
            t.setVariableFloat("x", FLAMEGPU.random.uniformFloat() * ENV_WIDTH)
            t.setVariableFloat("y", FLAMEGPU.random.uniformFloat() * ENV_WIDTH)