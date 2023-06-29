#! /usr/bin/env python3
from pyflamegpu import *
import sys, random, time
#from cuda import *
output=r'''
FLAMEGPU_AGENT_FUNCTION(output, flamegpu::MessageNone, flamegpu::MessageArray2D) {
    FLAMEGPU->message_out.setVariable<float>("value", FLAMEGPU->getVariable<float>("value"));
    FLAMEGPU->message_out.setIndex(FLAMEGPU->getVariable<unsigned int, 2>("pos", 0), FLAMEGPU->getVariable<unsigned int, 2>("pos", 1));
    return flamegpu::ALIVE;
}
'''

update=r'''
FLAMEGPU_AGENT_FUNCTION(update, flamegpu::MessageArray2D, flamegpu::MessageNone) {
    const unsigned int i = FLAMEGPU->getVariable<unsigned int, 2>("pos", 0);
    const unsigned int j = FLAMEGPU->getVariable<unsigned int, 2>("pos", 1);

    const float dx2 = FLAMEGPU->environment.getProperty<float>("dx2");
    const float dy2 = FLAMEGPU->environment.getProperty<float>("dy2");
    const float old_value = FLAMEGPU->getVariable<float>("value");

    const float left = FLAMEGPU->message_in.at(i == 0 ? FLAMEGPU->message_in.getDimX() - 1 : i - 1, j).getVariable<float>("value");
    const float up = FLAMEGPU->message_in.at(i, j == 0 ? FLAMEGPU->message_in.getDimY() - 1 : j - 1).getVariable<float>("value");
    const float right = FLAMEGPU->message_in.at(i + 1 >= FLAMEGPU->message_in.getDimX() ? 0 : i + 1, j).getVariable<float>("value");
    const float down = FLAMEGPU->message_in.at(i, j + 1 >= FLAMEGPU->message_in.getDimY() ? 0 : j + 1).getVariable<float>("value");

    // Explicit scheme
    float new_value = (left - 2.0 * old_value + right) / dx2 + (up - 2.0 * old_value + down) / dy2;

    const float a = FLAMEGPU->environment.getProperty<float>("a");
    const float dt = FLAMEGPU->environment.getProperty<float>("dt");

    new_value *= a * dt;
    new_value += old_value;

    FLAMEGPU->setVariable<float>("value", new_value);
    return flamegpu::ALIVE;
}
'''

def create_model():
#   创建模型，并且起名
    model = pyflamegpu.ModelDescription("Heat Equation")
    return model

def define_environment(model):
#   创建环境，给出一些不受模型影响的外生变量
    env = model.Environment()
    env.newPropertyUInt("SQRT_AGENT_COUNT", 200)
    env.newPropertyUInt("AGENT_COUNT", int(env.getPropertyUInt("SQRT_AGENT_COUNT")**2))  
    a = 0.5
    env.newPropertyFloat("a", a)
    dx = 0.01
    env.newPropertyFloat("dx", dx)
    dy = 0.01
    env.newPropertyFloat("dy", dy)
    dx2 = dx**2
    env.newPropertyFloat("dx2", dx2)
    dy2 = dy**2
    env.newPropertyFloat("dy2", dy2)
    dt = dx2 * dy2 / (2.0 * a * (dx2 + dy2))
    env.newPropertyFloat("dt", dt)
    return env

def define_messages(model, env):
#   创建信息，名为location，为agent之间传递的信息变量，还没太明白信息的作用，还需要琢磨下
    message = model.newMessageArray2D("temperature")
    message.newVariableFloat("value")
    message.setDimensions(env.getPropertyUInt("SQRT_AGENT_COUNT"), env.getPropertyUInt("SQRT_AGENT_COUNT"))
    
def define_agents(model):
#   创建agent，名为point，是agent自己的变量和函数。
    agent = model.newAgent("cell")
    agent.newVariableArrayUInt("pos", 2)
    agent.newVariableFloat("value")
    agent.newVariableFloat("x")
    agent.newVariableFloat("y")
#   有关信息的描述是FlameGPU2的关键特色，还需要进一步理解。
    out_fn = agent.newRTCFunction("output", output)
    out_fn.setMessageOutput("temperature")
    in_fn = agent.newRTCFunction("update", update)
    in_fn.setMessageInput("temperature")

def define_execution_order(model):
#   引入层主要目的是确定agent行动的顺序。
    layer = model.newLayer()
    layer.addAgentFunction("cell","output")
    layer = model.newLayer()
    layer.addAgentFunction("cell","update")

def initialise_simulation(seed):
    model = create_model()
    env = define_environment(model)
    define_messages(model, env)
    define_agents(model)
    define_execution_order(model)


    #   初始化cuda模拟
    cudaSimulation = pyflamegpu.CUDASimulation(model)
    cudaSimulation.initialise(sys.argv)

#   如果未提供 xml 模型文件，则生成一个填充。
    if not cudaSimulation.SimulationConfig().input_file:
#   在空间内均匀分布agent，具有均匀分布的初始速度。
        random.seed(cudaSimulation.SimulationConfig().random_seed)
        init_pop = pyflamegpu.AgentVector(model.Agent("cell"), env.getPropertyUInt("AGENT_COUNT"))
        for x in range(env.getPropertyUInt("SQRT_AGENT_COUNT")):
            for y in range(env.getPropertyUInt("SQRT_AGENT_COUNT")):
                init_pop.push_back()
                instance = init_pop.back()
                instance.setVariableArrayUInt("pos", (x,y))      
                instance.setVariableFloat("value", random.uniform(0.0, 1.0))                
                if pyflamegpu.VISUALISATION:
        # Agent position in space
                    instance.setVariableFloat("x", x)
                    instance.setVariableFloat("y", y)
        cudaSimulation.setPopulationData(init_pop)

#   设置可视化
    if pyflamegpu.VISUALISATION:
        visualisation = cudaSimulation.getVisualisation()
        visualisation.setBeginPaused(True)
#   设置相机所在位置和速度
        visualisation.setSimulationSpeed(5)
        visualisation.setInitialCameraLocation(env.getPropertyUInt("SQRT_AGENT_COUNT") / 2.0, env.getPropertyUInt("SQRT_AGENT_COUNT") / 2.0, 450.0)
        visualisation.setInitialCameraTarget(env.getPropertyUInt("SQRT_AGENT_COUNT") / 2.0, env.getPropertyUInt("SQRT_AGENT_COUNT") / 2.0, 0.0)
        visualisation.setCameraSpeed(0.001 * env.getPropertyUInt("SQRT_AGENT_COUNT"))
        visualisation.setViewClips(0.01, 2500)
        visualisation.setClearColor(0.0, 0.0, 0.0)
#   将“cell” agent添加到可视化中
        agt = visualisation.addAgent("cell")
        agt.setModel(pyflamegpu.CUBE)
        agt.setModelScale(1.0)
        agt.setColor(pyflamegpu.ViridisInterpolation("value", 0.35, 0.65))
#   打开可视化窗口
        visualisation.activate()
    cudaSimulation.simulate()



    if pyflamegpu.VISUALISATION:
        visualisation.join()

# Ensure profiling / memcheck work correctly
    pyflamegpu.cleanup()

if __name__ == "__main__":
    start=time.time()
    initialise_simulation(64)
    end=time.time()
    print(end-start)
    exit()