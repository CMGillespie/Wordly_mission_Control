#!/usr/bin/env python3
"""
test_split_probe.py — v0.1
One-shot diagnostic: connect to a live Wordly session as a bystander (no audio
ever sent) and send {"type": "split"}. Prints every message the server sends
back so we can see whether "split" is accepted without an active presenter/
audio connection, same pattern as the existing End Session WSS logic.

Usage: python3 test_split_probe.py SESSION-ID PASSCODE
"""
import asyncio
import json
import sys
import websockets

WS_ENDPOINT = "wss://endpoint.wordly.ai/session"

async def main(session_id, passcode):
    async with websockets.connect(WS_ENDPOINT) as ws:
        await ws.send(json.dumps({
            "type": "connect",
            "presentationCode": session_id,
            "accessKey": passcode,
        }))
        print("Sent connect. Waiting for response...")
        connect_resp = await ws.recv()
        print("CONNECT RESPONSE:", connect_resp)

        print("Sending split...")
        await ws.send(json.dumps({"type": "split"}))

        try:
            for _ in range(3):
                msg = await asyncio.wait_for(ws.recv(), timeout=3)
                print("RECEIVED:", msg)
        except asyncio.TimeoutError:
            print("No further messages after split (check the portal transcript to confirm either way).")

        print("Closing connection — session was NOT ended.")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 test_split_probe.py SESSION-ID PASSCODE")
        sys.exit(1)
    asyncio.run(main(sys.argv[1], sys.argv[2]))
