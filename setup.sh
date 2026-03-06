sudo apt-get update
sudo apt-get install git -y
sudo apt-get install python3-pip -y
sudo apt-get install python3-pil -y
sudo apt-get install python3-numpy -y
sudo pip3 install spidev

sudo apt install python3-gpiozero

sudo apt install python3-smbus

mv ./programme/data.example.json ./programme/data.json
sudo chmod 700 ./programme/data.json