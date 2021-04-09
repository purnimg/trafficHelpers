from ixnetwork_restpy import SessionAssistant
from ixnetwork_restpy import TestPlatform
import time
import pprint

#sw-ixia3.insieme.local is 172.31.194.141

session_assistant = SessionAssistant(IpAddress='172.31.194.141', 
    LogLevel=SessionAssistant.LOGLEVEL_INFO, 
    ClearConfig=True)

ixnetwork = session_assistant.Ixnetwork
test_platform = session_assistant.TestPlatform
test_platform.Trace = TestPlatform.TRACE_INFO


# create tx and rx port resources
port_map = session_assistant.PortMapAssistant()
port_map.Map('172.21.86.100', 9, 2, Name='Rx')
port_map.Map('172.21.86.100', 9, 14, Name='Tx')
#port_map.Map('172.21.86.100', 9, 6, Name='SupRx') keep adding more ports in Rx if needed for capturing

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
eth_s.Ipv4.add().Address.Single('23.1.1.2')
eth_s.Vlan.find().VlanId.Single('351')


eth_d = ixnetwork \
    .Topology.add(Vports=ixnetwork.Vport.find(Name='^Rx')) \
    .DeviceGroup.add(Multiplier='1') \
    .Ethernet.add()
    
eth_d.EnableVlans.Single(True)
eth_d.Ipv4.add().Address.Single('23.1.1.3')
eth_d.Vlan.find().VlanId.Single('351')
    
# create template
vlanT = ixnetwork.Traffic.ProtocolTemplate.find(StackTypeId='^vlan$')
arpT = ixnetwork.Traffic.ProtocolTemplate.find(StackTypeId='^ethernetARP$')


# create arp stream
traffic_item_arp = ixnetwork.Traffic.TrafficItem.add(Name='pyats-copp-arp', TrafficType='raw')

traffic_item_arp.EndpointSet.add(
    Sources=ixnetwork.Vport.find(Name='^Tx').Protocols.find(),
    Destinations=ixnetwork.Vport.find(Name='^Rx').Protocols.find())

traffic_config = traffic_item_arp.ConfigElement.find()
traffic_config.FrameRate.update(Type='framesPerSecond', Rate='1')
traffic_config.FrameSize.update(FixedSize='1024')
traffic_config.TransmissionControl.update(Type='continuous')#, BurstPacketCount='100', InterBurstGapUnits='nanoseconds', RepeatBurst='1000')

# create stack 
ethernet_stack = traffic_config.Stack.find(StackTypeId='^ethernet$')
vlan_stack = traffic_config.Stack.read(ethernet_stack.AppendProtocol(vlanT))
arp_stack = traffic_config.Stack.read(vlan_stack.AppendProtocol(arpT))

# adjust stack fields
destination_mac = ethernet_stack.Field.find(FieldTypeId='ethernet.header.destinationAddress')
destination_mac.update(ValueType='singleValue', SingleValue='00:22:BD:F8:19:FF', TrackingEnabled=True)
source_mac = ethernet_stack.Field.find(FieldTypeId='ethernet.header.sourceAddress')
source_mac.update(ValueType='singleValue', SingleValue='00:00:00:00:00:82')

vlan_stack.Field.find(FieldTypeId='vlan.header.vlanTag.vlanID').update(ValueType='singleValue', SingleValue='351', TrackingEnabled=True)
arp_stack.Field.find(FieldTypeId='ethernetARP.header.protocolType').update(ValueType='singleValue', SingleValue="0x0800")
arp_stack.Field.find(FieldTypeId='ethernetARP.header.srcHardwareAddress').update(ValueType='singleValue', SingleValue='00:00:00:00:00:82')
arp_stack.Field.find(FieldTypeId='ethernetARP.header.dstHardwareAddress').update(ValueType='singleValue', SingleValue='00:00:00:00:00:00')
arp_stack.Field.find(FieldTypeId='ethernetARP.header.srcIP').update(ValueType='singleValue', SingleValue='23.1.1.10')
arp_stack.Field.find(FieldTypeId='ethernetARP.header.dstIP').update(ValueType='singleValue', SingleValue='23.1.1.11')
arp_stack.Field.find(FieldTypeId='ethernetARP.header.opCode').update(ValueType='singleValue', SingleValue='1')

# connect ports to hardware test ports
# apply traffic to hardware
# start traffic
# push ConfigElement settings down to HighLevelStream resources
traffic_item_arp.Generate()
port_map.Connect(ForceOwnership=True)
ixnetwork.Traffic.Apply()
ixnetwork.Traffic.StartStatelessTrafficBlocking()
print("+++++++Waiting for 300 seconds ...")
time.sleep(300)

# print statistics
output = session_assistant.StatViewAssistant('Flow Statistics')
print(output)

# stop traffic
#ixnetwork.Traffic.StopStatelessTrafficBlocking()
# disable the traffic item
#traffic_item_arp.Enabled = "False"

print("+++++++DONE")
######################################
