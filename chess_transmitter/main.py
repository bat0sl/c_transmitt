import chess
import chess.engine
import asyncio
from kivy.app import App
from kivy.lang.builder import Builder
import bleak


kv = '''
Widget:
    TextInput:
        id: cm_input
        hint_text: "Chess Move Played"
        size: root.width*0.8, root.height*0.1
        font_size: self.height*0.3
        multiline: False
    Button: 
        id: cm_send
        text: "Move"
        size: root.width*0.2, root.height*0.1
        font_size: self.height*0.35
        pos: root.width*0.8, 0
        on_press: self.disabled = True
    Label:
        id: cm_status
        text: "No Status"
        size: root.width*0.2, root.height*0.05
        font_size: self.height*0.5
        pos: root.width*0.5-0.5*self.width, root.height*0.1
    TextInput:
        id: mac_input
        hint_text: "BLE MAC-Address"
        size: root.width*0.6, root.height*0.05
        font_size: self.height*0.5
        pos: 0, 0.95*root.height-self.height
        multiline: False
    Button:
        id: mac_connect
        text: "Connect"
        size: root.width*0.2, root.height*0.05
        font_size: self.height*0.35
        pos: root.width*0.8, 0.95*root.height-self.height
        on_press: app.mac_connect()
    Button:
        id: mac_disconnect
        text: "Disconnect"
        size: root.width*0.2, root.height*0.05
        font_size: self.height*0.35
        pos: root.width*0.6, 0.95*root.height-self.height
        on_press: self.disabled = True
    Label:
        id: mac_status
        text: "Disconnected"
        size: root.width*0.2, root.height*0.05
        font_size: self.height*0.5
        color: "red"
        pos: root.width*0.5-0.5*self.width, 0.9*root.height-self.height
    ToggleButton:
        id: white_player
        text: "White"
        size: root.width*0.2, root.height*0.05
        font_size: self.height*0.5
        pos: 0, root.height*0.1
        group: "player_color"
    ToggleButton:
        id: black_player
        text: "Black"
        size: root.width*0.2, root.height*0.05
        font_size: self.height*0.5
        pos: 0, root.height*0.85
        group: "player_color"
    Image:
        source: "board480.png"
        size: root.height*0.45, root.height*0.45
        pos: root.width*0.5-self.width*0.5, root.height*0.5-self.height*0.5
'''


class ChessGuiBle(App):   
    def build(self): 
        return Builder.load_string(kv) #Load widgets

    def mac_connect(self): #Function for when "connect" button hass been pressed
        #Check for MAC-address spelling (Only Checks for lenght and first colon for convenience)
        self.root.ids.mac_connect.disabled = True #Avoid multiple conenctions
        if len(self.root.ids.mac_input.text) == 17 and self.root.ids.mac_input.text[2] == ":":
            asyncio.create_task(self.connection())
        else:
            self.root.ids.mac_status.text = "Invalid MAC-address"
            self.root.ids.mac_status.color = "red"
            self.root.ids.mac_connect.disabled = False

    def on_disconnect(self,client):
        self.root.ids.mac_status.text = "Connection Lost"
        self.root.ids.mac_status.color = "red"
        self.root.ids.mac_connect.disabled = False
        connection = False

    async def connection(self):
        client = bleak.BleakClient(self.root.ids.mac_input.text)
        client.set_disconnected_callback(self.on_disconnect)    
        self.root.ids.mac_status.text = "Connecting..."
        self.root.ids.mac_status.color = "yellow"
        try:
            await client.connect()
            self.root.ids.mac_status.text = "Connected to " + self.root.ids.mac_input.text
            self.root.ids.mac_status.color = "green"
            self.root.ids.mac_disconnect.disabled = False
        except:
            self.root.ids.mac_status.text = "Connection Failed"
            self.root.ids.mac_status.color = "red"
            self.root.ids.mac_connect.disabled = False
            return
        engine = chess.engine.SimpleEngine.popen_uci(r"stockfish-windows.exe")
        board = chess.Board()
        self.root.ids.white_player.state = "normal"
        self.root.ids.black_player.state = "normal"
        while self.root.ids.white_player.state == "normal" and self.root.ids.black_player.state == "normal":
            self.root.ids.cm_status.text = "Choose a player to help."
            await asyncio.sleep(2)
        if self.root.ids.white_player.state == "down":
            bestmove = engine.play(board, chess.engine.Limit(time=0.5))
            await client.write_gatt_char("FF46F9D0-6833-4968-A3E4-5F80932CA0B3", str(bestmove.move).encode("utf-8"))
        while self.root.ids.mac_disconnect.disabled == False: #handles "cm_input" while "disconnect" button remains untouched
            if self.root.ids.cm_send.disabled == True:
                cm = self.root.ids.cm_input.text
                if not board.is_game_over():
                    while True and self.root.ids.cm_send.disabled == True:
                        try:
                            # Try to make the move
                            board.push_san(cm)
                            self.root.ids.board.text = board
                            break
                        except ValueError:
                            self.root.ids.cm_input.text = ""
                            self.root.ids.cm_send.disabled = False
                            print("Invalid move. Try again.")
                            await asyncio.sleep(1)
                else:
                    engine.quit()
                    break
                if board.turn == chess.WHITE and self.root.ids.white_player.state == "down":
                    bestmove = engine.play(board, chess.engine.Limit(time=0.5))
                    await client.write_gatt_char("FF46F9D0-6833-4968-A3E4-5F80932CA0B3", str(bestmove.move).encode("utf-8"))
                elif board.turn == chess.BLACK and self.root.ids.black_player.state == "down":
                    bestmove = engine.play(board, chess.engine.Limit(time=0.5))
                    await client.write_gatt_char("FF46F9D0-6833-4968-A3E4-5F80932CA0B3", str(bestmove.move).encode("utf-8"))
            await asyncio.sleep(2)
        self.root.ids.mac_status.text = "Disconnecting..."
        await client.disconnect()
        self.root.ids.mac_status.text = "Disconnected by User"
        self.root.ids.mac_status.color = "red"

asyncio.run(ChessGuiBle().async_run('asyncio'))