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
port_map.Map('172.21.86.100', 9, 14, Name='Rx')
port_map.Map('172.21.86.100', 9, 2, Name='Tx')
#port_map.Map('172.21.86.100', 9, 6, Name='Rx1')

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
eth_s.Ipv4.add().Address.Single('50.1.1.2')
eth_s.Vlan.find().VlanId.Single('351')


eth_d = ixnetwork \
    .Topology.add(Vports=ixnetwork.Vport.find(Name='^Rx')) \
    .DeviceGroup.add(Multiplier='1') \
    .Ethernet.add()
    
eth_d.EnableVlans.Single(True)
eth_d.Ipv4.add().Address.Single('50.1.1.12')
eth_d.Vlan.find().VlanId.Single('351')
    
# create template
vlanT = ixnetwork.Traffic.ProtocolTemplate.find(StackTypeId='^vlan$')
arpT = ixnetwork.Traffic.ProtocolTemplate.find(StackTypeId='^ethernetARP$')
ipv4T = ixnetwork.Traffic.ProtocolTemplate.find(StackTypeId='^ipv4$')
udpT = ixnetwork.Traffic.ProtocolTemplate.find(StackTypeId='^udp$')
ptpT = ixnetwork.Traffic.ProtocolTemplate.find(StackTypeId='^PTPv2$')


# create arp stream
traffic_item_arp = ixnetwork.Traffic.TrafficItem.add(Name='pyats-copp-arp', TrafficType='raw')

traffic_item_arp.EndpointSet.add(
    Sources=ixnetwork.Vport.find(Name='^Tx').Protocols.find(),
    Destinations=ixnetwork.Vport.find(Name='^Rx').Protocols.find())

traffic_config = traffic_item_arp.ConfigElement.find()
traffic_config.FrameRate.update(Type='framesPerSecond', Rate='3')
traffic_config.FrameSize.update(FixedSize='1024')
traffic_config.TransmissionControl.update(Type='continuous')#, BurstPacketCount='100', InterBurstGapUnits='nanoseconds', RepeatBurst='1000')

# create stack 
ethernet_stack = traffic_config.Stack.find(StackTypeId='^ethernet$')
vlan_stack = traffic_config.Stack.read(ethernet_stack.AppendProtocol(vlanT))
arp_stack = traffic_config.Stack.read(vlan_stack.AppendProtocol(arpT))

# adjust stack fields
destination_mac = ethernet_stack.Field.find(FieldTypeId='ethernet.header.destinationAddress')
destination_mac.update(ValueType='singleValue', SingleValue='ff:ff:ff:ff:ff:ff', TrackingEnabled=True)
source_mac = ethernet_stack.Field.find(FieldTypeId='ethernet.header.sourceAddress')
source_mac.update(ValueType='singleValue', SingleValue='00:00:00:00:00:82')

vlan_stack.Field.find(FieldTypeId='vlan.header.vlanTag.vlanID').update(ValueType='singleValue', SingleValue='351', TrackingEnabled=True)
arp_stack.Field.find(FieldTypeId='ethernetARP.header.protocolType').update(ValueType='singleValue', SingleValue="0x0800")
arp_stack.Field.find(FieldTypeId='ethernetARP.header.srcHardwareAddress').update(ValueType='singleValue', SingleValue='00:00:00:00:00:82')
arp_stack.Field.find(FieldTypeId='ethernetARP.header.dstHardwareAddress').update(ValueType='singleValue', SingleValue='00:00:00:00:00:00')
arp_stack.Field.find(FieldTypeId='ethernetARP.header.srcIP').update(ValueType='singleValue', SingleValue='23.1.1.10')
arp_stack.Field.find(FieldTypeId='ethernetARP.header.dstIP').update(ValueType='singleValue', SingleValue='23.1.1.1')
arp_stack.Field.find(FieldTypeId='ethernetARP.header.opCode').update(ValueType='singleValue', SingleValue='1')

# connect ports to hardware test ports
# apply traffic to hardware
# start traffic
# push ConfigElement settings down to HighLevelStream resources
traffic_item_arp.Generate()
port_map.Connect(ForceOwnership=True)
ixnetwork.Traffic.Apply()
ixnetwork.Traffic.StartStatelessTrafficBlocking()
time.sleep(30)

# print statistics
output = session_assistant.StatViewAssistant('Flow Statistics')
print(output)

# stop traffic
ixnetwork.Traffic.StopStatelessTrafficBlocking()
# disable the traffic item
traffic_item_arp.Enabled = "False"

print("+++++++DONE")
######################################
# create ospf stream
traffic_item_ospf = ixnetwork.Traffic.TrafficItem.add(Name='pyats-copp-ospf', TrafficType='raw')
traffic_item_ospf.EndpointSet.add(
    Sources=ixnetwork.Vport.find(Name='^Tx').Protocols.find(),
    Destinations=ixnetwork.Vport.find(Name='^Rx').Protocols.find())

traffic_config = traffic_item_ospf.ConfigElement.find()
traffic_config.FrameRate.update(Type='framesPerSecond', Rate='1500')
traffic_config.FrameSize.update(FixedSize='1024')
traffic_config.TransmissionControl.update(Type='continuous')#, BurstPacketCount='100', InterBurstGapUnits='nanoseconds', RepeatBurst='1000')

# create stack 
ethernet_stack = traffic_config.Stack.find(StackTypeId='^ethernet$')
vlan_stack = traffic_config.Stack.read(ethernet_stack.AppendProtocol(vlanT))
ipv4_stack = traffic_config.Stack.read(vlan_stack.AppendProtocol(ipv4T))
ospfv2Hello_stack = traffic_config.Stack.read(ipv4_stack.AppendProtocol(ospfT))

# adjust stack fields
destination_mac = ethernet_stack.Field.find(FieldTypeId='ethernet.header.destinationAddress')
destination_mac.update(ValueType='singleValue', SingleValue='00:22:bd:f8:19:ff', TrackingEnabled=True)
source_mac = ethernet_stack.Field.find(FieldTypeId='ethernet.header.sourceAddress')
source_mac.update(ValueType='singleValue', SingleValue='00:00:00:00:00:82')

vlan_stack.Field.find(FieldTypeId='vlan.header.vlanTag.vlanID').update(ValueType='singleValue', SingleValue='851', TrackingEnabled=True)
ipv4_stack.Field.find(FieldTypeId='ipv4.header.srcIp').update(
                    ValueType='singleValue', SingleValue='8.1.1.2')
ipv4_stack.Field.find(FieldTypeId='ipv4.header.dstIp').update(
                    ValueType='singleValue', SingleValue='224.0.0.5')

traffic_item_ospf.Generate()
port_map.Connect(ForceOwnership=True)
ixnetwork.Traffic.Apply()
ixnetwork.Traffic.StartStatelessTrafficBlocking()
time.sleep(30)
ixnetwork.Traffic.StopStatelessTrafficBlocking()
# print flow statistics
pprint.pprint(session_assistant.StatViewAssistant('Flow Statistics'))
# disable the traffic item
traffic_item_ospf.Enabled = "False"

##################################################
# create dhcp stream
traffic_item_dhcp = ixnetwork.Traffic.TrafficItem.add(Name='pyats-copp-dhcp', TrafficType='raw')
traffic_item_dhcp.EndpointSet.add(
    Sources=ixnetwork.Vport.find(Name='^Tx').Protocols.find(),
    Destinations=ixnetwork.Vport.find(Name='^Rx').Protocols.find())
traffic_config = traffic_item_dhcp.ConfigElement.find()
#traffic_config.FrameRate.update(Type='percentLineRate', Rate='10')
traffic_config.FrameRate.update(Type='framesPerSecond', Rate='1500')
traffic_config.FrameSize.update(FixedSize='1024')
traffic_config.TransmissionControl.update(Type='continuous')#, BurstPacketCount='100', InterBurstGapUnits='nanoseconds', RepeatBurst='1000')

# create stack 
ethernet_stack = traffic_config.Stack.find(StackTypeId='^ethernet$')
vlan_stack = traffic_config.Stack.read(ethernet_stack.AppendProtocol(vlanT))
ipv4_stack = traffic_config.Stack.read(vlan_stack.AppendProtocol(ipv4T))
udp_stack = traffic_config.Stack.read(ipv4_stack.AppendProtocol(udpT))

# adjust stack fields
destination_mac = ethernet_stack.Field.find(FieldTypeId='ethernet.header.destinationAddress')
destination_mac.update(ValueType='singleValue', SingleValue='00:22:bd:f8:19:ff', TrackingEnabled=True)
source_mac = ethernet_stack.Field.find(FieldTypeId='ethernet.header.sourceAddress')
source_mac.update(ValueType='singleValue', SingleValue='00:00:00:00:00:82')

vlan_stack.Field.find(FieldTypeId='vlan.header.vlanTag.vlanID').update(ValueType='singleValue', SingleValue='851', TrackingEnabled=True)
ipv4_stack.Field.find(FieldTypeId='ipv4.header.srcIp').update(
                    ValueType='singleValue', SingleValue='50.1.1.2')
ipv4_stack.Field.find(FieldTypeId='ipv4.header.dstIp').update(
                    ValueType='singleValue', SingleValue='8.1.1.1')
udp_stack.Field.find(FieldTypeId='udp.header.srcPort').update(
                    ValueType='singleValue', SingleValue='68')
udp_stack.Field.find(FieldTypeId='udp.header.dstPort').update(
                    ValueType='singleValue', SingleValue='67')


traffic_item_dhcp.Generate()
port_map.Connect(ForceOwnership=True)
ixnetwork.Traffic.Apply()
ixnetwork.Traffic.StartStatelessTrafficBlocking()
time.sleep(30)
ixnetwork.Traffic.StopStatelessTrafficBlocking()

# print statistics
traffic_statistics = session_assistant.StatViewAssistant('Flow Statistics')
traffic_statistics1 = session_assistant.StatViewAssistant('Traffic Item Statistics')
print(traffic_statistics)
print(traffic_statistics1)
tx_frames = traffic_statistics.Rows[0]['Tx Frames']
ixnetwork.info('tx frames: %s' % tx_frames)
########################################################      
