sudo apt-get update
sudo apt-get install git -y
sudo apt-get install python3-pip -y
sudo apt-get install python3-pil -y
sudo apt-get install python3-numpy -y
sudo apt install python3-gpiozero
sudo apt install python3-smbus

sudo pip3 install spidev

cp ./programme/data.example.json ./programme/data.json
sudo chmod 700 ./programme/data.json

sudo cp ./sw-keybox.service /etc/systemd/system/sw-keybox.service
sudo chown root:root /etc/systemd/system/sw-keybox.service
sudo chmod 755 /etc/systemd/system/sw-keybox.service

sudo systemctl daemon-reload
sudo systemctl enable sw-keybox.service
sudo systemctl start sw-keybox.service
sudo reboot