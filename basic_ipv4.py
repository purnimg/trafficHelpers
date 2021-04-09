from ixnetwork_restpy import SessionAssistant
from ixnetwork_restpy import TestPlatform
import time
import pprint

session_assistant = SessionAssistant(IpAddress='172.31.194.141', 
    LogLevel=SessionAssistant.LOGLEVEL_INFO, 
    ClearConfig=True)

ixnetwork = session_assistant.Ixnetwork
test_platform = session_assistant.TestPlatform
test_platform.Trace = TestPlatform.TRACE_INFO


# create tx and rx port resources
port_map = session_assistant.PortMapAssistant()
port_map.Map('172.21.86.100', 9, 14, Name='Tx')
port_map.Map('172.21.86.100', 9, 2, Name='Rx')

eth = test_platform.Sessions.find().Ixnetwork.Vport.find(Name='^Tx').L1Config.Ethernet
eth.Media = 'fiber'
eth = test_platform.Sessions.find().Ixnetwork.Vport.find(Name='^Rx').L1Config.Ethernet
eth.Media = 'fiber'

# create a TrafficItem resource

#create topology
eth_s = ixnetwork \
        .Topology.add(Vports=ixnetwork.Vport.find(Name='^Tx')) \
        .DeviceGroup.add(Multiplier='1') \
	    .Ethernet.add()
    
eth_s.EnableVlans.Single(True)
eth_s.find().Mac.Single('00:00:00:00:01:12')
eth_s.Ipv4.add().Address.Single('50.1.1.12')
eth_s.Ipv4.find().GatewayIp.Single('50.1.1.1')
eth_s.Vlan.find().VlanId.Single('351')


eth_d = ixnetwork \
    .Topology.add(Vports=ixnetwork.Vport.find(Name='^Rx')) \
    .DeviceGroup.add(Multiplier='1') \
    .Ethernet.add()
    
eth_d.EnableVlans.Single(True)
eth_d.find().Mac.Single('00:00:00:00:01:13')
eth_d.Ipv4.add().Address.Single('50.1.1.13')
eth_d.Ipv4.find().GatewayIp.Single('50.1.1.1')
eth_d.Vlan.find().VlanId.Single('351')
    
# create template
vlanT = ixnetwork.Traffic.ProtocolTemplate.find(StackTypeId='^vlan$')
ipv4T = ixnetwork.Traffic.ProtocolTemplate.find(StackTypeId='^ipv4$')
tcpT = ixnetwork.Traffic.ProtocolTemplate.find(StackTypeId='^tcp$')

traffic_item_tx = ixnetwork.Traffic.TrafficItem.add(Name='pyats-tcp-tx', TrafficType='raw')
traffic_item_tx.EndpointSet.add(
    Sources=ixnetwork.Vport.find(Name='^Tx').Protocols.find(),
    Destinations=ixnetwork.Vport.find(Name='^Rx').Protocols.find())

traffic_item_rx = ixnetwork.Traffic.TrafficItem.add(Name='pyats-tcp-rx', TrafficType='raw')
traffic_item_rx.EndpointSet.add(
    Sources=ixnetwork.Vport.find(Name='^Rx').Protocols.find(),
    Destinations=ixnetwork.Vport.find(Name='^Tx').Protocols.find())

# create tcp stream TX
traffic_config = traffic_item_tx.ConfigElement.find()
traffic_config.FrameRate.update(Type='framesPerSecond', Rate='1000')
traffic_config.FrameSize.update(FixedSize='1024')
traffic_config.TransmissionControl.update(Type='continuous')#, BurstPacketCount='100', InterBurstGapUnits='nanoseconds', RepeatBurst='1000')        

# create stack 
ethernet_stack = traffic_config.Stack.find(StackTypeId='^ethernet$')
vlan_stack = traffic_config.Stack.read(ethernet_stack.AppendProtocol(vlanT))
ipv4_stack = traffic_config.Stack.read(vlan_stack.AppendProtocol(ipv4T))
tcp_stack = traffic_config.Stack.read(ipv4_stack.AppendProtocol(tcpT))

# adjust stack fields
destination_mac = ethernet_stack.Field.find(FieldTypeId='ethernet.header.destinationAddress')
destination_mac.update(ValueType='singleValue', SingleValue='00:22:bd:f8:19:ff', TrackingEnabled=True)
source_mac = ethernet_stack.Field.find(FieldTypeId='ethernet.header.sourceAddress')
source_mac.update(ValueType='singleValue', SingleValue='00:00:00:00:01:12')

vlan_stack.Field.find(FieldTypeId='vlan.header.vlanTag.vlanID').update(ValueType='singleValue', SingleValue='351', TrackingEnabled=True)
ipv4_stack.Field.find(FieldTypeId='ipv4.header.srcIp').update(
                    ValueType='singleValue', SingleValue='50.1.1.12')
ipv4_stack.Field.find(FieldTypeId='ipv4.header.dstIp').update(
                    ValueType='singleValue', SingleValue='50.1.1.13')


# create tcp stream RX
traffic_config = traffic_item_rx.ConfigElement.find()
traffic_config.FrameRate.update(Type='framesPerSecond', Rate='1000')
traffic_config.FrameSize.update(FixedSize='1024')
traffic_config.TransmissionControl.update(Type='continuous')#, BurstPacketCount='100', InterBurstGapUnits='nanoseconds', RepeatBurst='1000')        

# create stack 
ethernet_stack = traffic_config.Stack.find(StackTypeId='^ethernet$')
vlan_stack = traffic_config.Stack.read(ethernet_stack.AppendProtocol(vlanT))
ipv4_stack = traffic_config.Stack.read(vlan_stack.AppendProtocol(ipv4T))
tcp_stack = traffic_config.Stack.read(ipv4_stack.AppendProtocol(tcpT))

# adjust stack fields
destination_mac = ethernet_stack.Field.find(FieldTypeId='ethernet.header.destinationAddress')
destination_mac.update(ValueType='singleValue', SingleValue='00:22:bd:f8:19:ff', TrackingEnabled=True)
source_mac = ethernet_stack.Field.find(FieldTypeId='ethernet.header.sourceAddress')
source_mac.update(ValueType='singleValue', SingleValue='00:00:00:00:01:13')

vlan_stack.Field.find(FieldTypeId='vlan.header.vlanTag.vlanID').update(ValueType='singleValue', SingleValue='351', TrackingEnabled=True)
ipv4_stack.Field.find(FieldTypeId='ipv4.header.srcIp').update(
                    ValueType='singleValue', SingleValue='50.1.1.13')
ipv4_stack.Field.find(FieldTypeId='ipv4.header.dstIp').update(
                    ValueType='singleValue', SingleValue='50.1.1.12')


# push ConfigElement settings down to HighLevelStream resources
traffic_item_tx.Generate()
traffic_item_rx.Generate()
port_map.Connect(ForceOwnership=True)
ixnetwork.Traffic.Apply()
ixnetwork.Traffic.StartStatelessTrafficBlocking()
time.sleep(300)
ixnetwork.Traffic.StopStatelessTrafficBlocking()
# traffic_item_tx.Enabled = "False"
traffic_statistics = session_assistant.StatViewAssistant('Flow Statistics')
txFrames = traffic_statistics.Rows[0]['Tx Frames']
rxFrames = traffic_statistics.Rows[0]['Rx Frames']
ixnetwork.info('+++++ Tx Frames: %s' % txFrames)
ixnetwork.info('+++++ Rx Frames: %s' % rxFrames)
