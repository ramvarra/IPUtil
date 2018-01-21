

require 'CSV'
require 'ipaddr'

ip_ranges_filename = 'ipranges.csv'

CSV.foreach(ip_ranges_filename, headers: true) do |row|
  i = 0
  puts "#{i}: #{row}"
  if row.size < 2
    raise "Row must have atleast 2 values [IPRANGE, ATTRIB]"
  end

  begin
    if row[0].include?('-')
      first_ip, last_ip = row[0].strip().split('-').map {|x| IPAddr.new x.strip}
      puts "#{first_ip} .. #{last_ip}"
      ip_range = first_ip..last_ip
    else
      ip_range = (IPAddr.new row[0].strip).to_range
    end
  rescue Exception => ex
    puts "Exception while processing address #{row[0]} in row #{row}: #{ex.message}"
    puts ex.backtrace.inspect
    raise "Failed to process CSV IP Range file: #{ip_ranges_filename}"
  end

  puts "Row = #{row}"
  puts "IP: #{ip_range.inspect}"
end
