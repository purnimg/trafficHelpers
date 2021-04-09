from ixnetwork_restpy import SessionAssistant

session_assistant = SessionAssistant(IpAddress='172.31.194.141', 
    LogLevel=SessionAssistant.LOGLEVEL_INFO, 
    ClearConfig=True)
ixnetwork = session_assistant.Ixnetwork


#create vport to physical port mapping using PortMapAssistant
port_map = session_assistant.PortMapAssistant()
chassis_ip = '172.21.86.100'
lag_ports = [
    dict(Arg1=chassis_ip, Arg2=10, Arg3=17),
    dict(Arg1=chassis_ip, Arg2=10, Arg3=18)
]

port_map.Map('172.21.86.100', 10, 19, Name='VpcRx')


vports_1 = ixnetwork.Vport.add().add()
connected_ports = ixnetwork.AssignPorts(lag_ports, [], vports_1, True)
lag_1 = ixnetwork.Lag.add(Name='Lag 1', Vports=vports_1)
lag_1.ProtocolStack.add().Ethernet.add().Lagportlacp.add()

vports_2 = ixnetwork.Vport.find(Name='^VpcRx')

ethernet1 = ixnetwork.Topology.add(Ports=lag_1).DeviceGroup.add(Multiplier = 1).Ethernet.add()
ethernet2 = ixnetwork.Topology.add(Ports=vports_2).DeviceGroup.add(Multiplier = 1).Ethernet.add()

traffic_item = ixnetwork.Traffic.TrafficItem.add(Name='Lag Traffic pyats', TrafficType='raw')
endpoint_set = traffic_item.EndpointSet.add(Destinations=vports_2.Protocols.find(), Sources=lag_1)


