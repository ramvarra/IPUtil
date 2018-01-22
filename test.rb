

require 'CSV'
require 'ipaddr'
require './iputil.rb'

#==================================================================================================================
if __FILE__ == $0
  ip_ranges_filename = 'ipranges.csv'

  ipu = IPUtil.new(ip_ranges_filename)
  ip_list = ["192.168.1.25", "192.168.1.135", "192.168.1.136", "192.168.1.61", "10.30.3.1"]
  ip_list.each do |x|
    info = ipu.lookup_ip(x)
    if not info.nil?
      puts "#{x} = #{info['RANGE']} #{info['INFO']}"
    else
      puts "#{x} NOT FOUND"
    end
  end
end
