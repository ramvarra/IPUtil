

require 'CSV'
require 'ipaddr'

ip_ranges_filename = 'ipranges.csv'

csv_options = {:headers => true, :skip_blanks => true}

# structure of SubnetInfos (SubnetInfosV4, SubnetInfosV6)
#  SubnetInfos = {
#  size1 =>  [SubnetInfo1.1, SubnetInfo1.2, ...]},
#  size2 =>  [SubnetInfo2.1, SubnetInfo2.2, ...]},
#  ...
# }
# size1, size2, ... are integers representig the size of the range_info
# SubnetInfos is sorted by size (key). Each value is sorted by BEGIN
# SubnetInfo = {
#      'RANGE' => ip_range,
#      'INFO' => <dict.info_to_return - range, attribs>
#
#}
#
#
def sort_subnet_infos(subnet_infos)
  new_subnet_infos = subnet_infos.sort_by {|k, v| k}.to_h
  new_subnet_infos.keys.each do |k|
    v = new_subnet_infos[k].sort {|a, b| a['RANGE'].begin <=> b['RANGE'].begin}
    new_subnet_infos[k] = v
  end
  return new_subnet_infos
end



def show_subnet_infos(sis)
  t = '  '
  sis.each do |size, subnet_info_list|
    puts "SIZE: #{size}"
    subnet_info_list.each do |subnet_info|
      range = subnet_info['RANGE']
      info = subnet_info['INFO']
      puts "#{t}#{range}:    #{info}"
    end
  end
end

def ip_bsearch(info_list, ipa)
  first = 0
  last = info_list.size - 1
  while first <= last
    i = (first + last) / 2
    r = info_list[i]['RANGE']
    if r === ipa
      return info_list[i]
    end
    if ipa < r.begin
      last -= 1
    elsif ipa > r.end
      first += 1
    else
      return nil
    end
  end
  return nil
end

def lookup_ip(ip, subnet_infos_v4, subnet_infos_v6)
  ipa = IPAddr.new(ip)
  subnet_infos = if ipa.ipv4? then
    subnet_infos_v4
  elsif ipa.ipv6? then
    subnet_infos_v6
  else
    raise "Invalid IP Address #{ip} - neither v4 nor v6"
  end

  # find match in each info_list
  subnet_infos.each do |k, v|
    # binary search v for ipa
    # puts "checkig size #{k}"
    r = ip_bsearch(v, ipa)
    if not r.nil?
      return r
    end
  end

  return nil
end



subnet_infos_v4 = {}
subnet_infos_v6 = {}

CSV.foreach(ip_ranges_filename, csv_options).with_index() do |row, i|
  if row.size < 2
    raise "Row must have atleast 2 values [IPRANGE, ATTRIB]"
  end

  # build subnet range
  begin

    puts "ROW: #{row}"
    # if subnet is of the formt ip_first-ip_last, split it acorss '-'
    # and create range
    if row[0].include?('-')
      ip_list = row[0].split('-')
      if ip_list.size > 2
        raise "Bad IP Address range #{row[0]}, too many dashes in row: #{row} in file #{ip_ranges_filename}:#{i+2}"
      end
      first_ip, last_ip = ip_list.map {|x| IPAddr.new x.strip}
      ip_range = first_ip..last_ip
    else
      ip_range = (IPAddr.new row[0].strip).to_range
    end
  rescue Exception => ex
    raise "Exception while processing address #{row[0]} in row #{row} in #{ip_ranges_filename}:#{i+2}: #{ex.message}"
  end

  # calcualate subnet size
  range_size = ip_range.end.to_i - ip_range.begin.to_i + 1
  if range_size < 1
    raise "Bad Range #{row[0]} in row #{row} in #{ip_ranges_filename}:#{i+2}"
  end

  subnet_infos = if ip_range.begin.ipv4? then
    subnet_infos_v4
  elsif ip_range.begin.ipv6? then
    subnet_infos_v6
  else
    raise "Invalid range: #{ip_range} at #{ip_ranges_filename}:#{i+2}. Neither V4 nor V6!"
  end

  # check if dict with range_size key exists

  puts "RangeSize: #{range_size} #{range_size.class}"
  subnet_info_list = subnet_infos[range_size]
  if subnet_info_list.nil?
    subnet_info_list = subnet_infos[range_size] = []
  end

  # build SubnetInfo
  subnet_info = {'RANGE' => ip_range, 'INFO' => row}
  subnet_info_list.push(subnet_info)

end

puts "SUBNET_V4"
show_subnet_infos(subnet_infos_v4)
puts "SUBNET_V6"
show_subnet_infos(subnet_infos_v6)

# sort subnet_infos by range_size
subnet_infos_v4 = sort_subnet_infos(subnet_infos_v4)
subnet_infos_v6 = sort_subnet_infos(subnet_infos_v6)

# sort each info_list by begin



puts "SUBNET_V4"
show_subnet_infos(subnet_infos_v4)
puts "SUBNET_V6"
show_subnet_infos(subnet_infos_v6)

ip_list = ["192.168.1.25", "192.168.1.135", "192.168.1.136", "192.168.1.61", "10.30.3.1"]
ip_list.each do |x|
  info = lookup_ip(x, subnet_infos_v4, subnet_infos_v6)
  if not info.nil?
    puts "#{x} = #{info['RANGE']}"
  else
    puts "#{x} NOT FOUND"
  end
end
