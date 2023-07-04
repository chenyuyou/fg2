from pyflamegpu import *
import time, sys, random
from cuda import *

AddOffset = r"""
FLAMEGPU_AGENT_FUNCTION(AddOffset, flamegpu::MessageNone, flamegpu::MessageNone) {
    // Output each agents publicly visible properties.
    FLAMEGPU->setVariable<int>("x", FLAMEGPU->getVariable<int>("x") + FLAMEGPU->environment.getProperty<int>("offset"));
    return flamegpu::ALIVE;
}
"""

class initfn(pyflamegpu.HostFunction):
    def run(self, FLAMEGPU):
        # Fetch the desired agent count and environment width
        POPULATION_TO_GENERATE = FLAMEGPU.environment.getPropertyInt("POPULATION_TO_GENERATE")
        Init = FLAMEGPU.environment.getPropertyInt("init")
        Init_offset = FLAMEGPU.environment.getPropertyInt("init_offset")
        # Create agents
        agent = FLAMEGPU.agent("Agent")
        for i in range(POPULATION_TO_GENERATE):
            agent.newAgent().setVariableInt("x", Init + i * Init_offset)

class exitfn(pyflamegpu.HostFunction):
    def run(self, FLAMEGPU):
        # Fetch the desired agent count and environment width
        atomic_init += FLAMEGPU.environment.getPropertyInt("init")
        atomic_result += FLAMEGPU.agent("Agent").sumInt("x")


def create_model():
#   创建模型，并且起名
    model = pyflamegpu.ModelDescription("boids_spatial3D")
    return model

def define_environment(model):
#   创建环境，给出一些不受模型影响的外生变量
    env = model.Environment()
    env.newPropertyUInt("POPULATION_TO_GENERATE", 100000, True)
    env.newPropertyUInt("STEPS", 10)
    env.newPropertyUInt("init", 0)
    env.newPropertyUInt("init_offset", 1)
    env.newPropertyUInt("offset", 10)
    return env

def define_messages(model, env):
#   创建信息，名为location，为agent之间传递的信息变量，还没太明白信息的作用，还需要琢磨下
    pass

def define_agents(model):
#   创建agent，名为point，是agent自己的变量和函数。
    agent = model.newAgent("Agent")
    agent.newVariableFloat("x")
#   有关信息的描述是FlameGPU2的关键特色，还需要进一步理解。
    agent.newRTCFunction("AddOffset", AddOffset)


def define_execution_order(model):
#   引入层主要目的是确定agent行动的顺序。
    layer = model.newLayer()
    layer.addAgentFunction("AddOffset", "AddOffset")
    model.addInitFunction(initfn())
    model.addExitFunction(exitfn())

def initialise_simulation(seed):
    model = create_model()
    env = define_environment(model)
    define_messages(model, env)
    define_agents(model)
    define_execution_order(model)
#   初始化cuda模拟
    cudaSimulation = pyflamegpu.CUDASimulation(model)
    cudaSimulation.initialise(sys.argv)

#   设置可视化
    if pyflamegpu.VISUALISATION:
        m_vis = cudaSimulation.getVisualisation()
#   设置相机所在位置和速度
        INIT_CAM = env.getPropertyFloat("ENV_WIDTH")/2
        m_vis.setInitialCameraTarget(INIT_CAM, INIT_CAM, 0)
        m_vis.setInitialCameraLocation(INIT_CAM, INIT_CAM, env.getPropertyFloat("ENV_WIDTH"))
        m_vis.setCameraSpeed(0.01)
        m_vis.setSimulationSpeed(25)
#   将“point” agent添加到可视化中
        point_agt = m_vis.addAgent("point")
#   设置“point” agent的形状和大小
        point_agt.setModel(pyflamegpu.ICOSPHERE)
        point_agt.setModelScale(1/10.0)
#   标记环境边界 
        pen = m_vis.newPolylineSketch(1, 1, 1, 0.2)
        pen.addVertex(0, 0, 0)
        pen.addVertex(0, env.getPropertyFloat("ENV_WIDTH"), 0)
        pen.addVertex(env.getPropertyFloat("ENV_WIDTH"), env.getPropertyFloat("ENV_WIDTH"), 0)
        pen.addVertex(env.getPropertyFloat("ENV_WIDTH"), 0, 0)
        pen.addVertex(0, 0, 0)
#   打开可视化窗口
        m_vis.activate()
    
#   如果未提供 xml 模型文件，则生成一个填充。
    if not cudaSimulation.SimulationConfig().input_file:
#   在空间内均匀分布agent，具有均匀分布的初始速度。
        random.seed(cudaSimulation.SimulationConfig().random_seed)
        population = pyflamegpu.AgentVector(model.Agent("point"), env.getPropertyUInt("AGENT_COUNT"))
        for i in range(env.getPropertyUInt("AGENT_COUNT")):
            instance = population[i]
            instance.setVariableFloat("x",  random.uniform(0.0, env.getPropertyFloat("ENV_WIDTH")))
            instance.setVariableFloat("y",  random.uniform(0.0, env.getPropertyFloat("ENV_WIDTH")))
        cudaSimulation.setPopulationData(population)
    cudaSimulation.simulate()

    if pyflamegpu.VISUALISATION:
    # 模拟完成后保持可视化窗口处于活动状态
        m_vis.join()

if __name__ == "__main__":
    start=time.time()
    initialise_simulation(64)
    end=time.time()
    print(end-start)
    exit()