import os
import random
import click
import attr
import requests
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import cherrypy
import nexmo


intro = """
▄▄▌ ▐ ▄▌ ▄ .▄ ▄▄▄· • ▌ ▄ ·.  ▄▄▄·  ▄▄ • ▄▄▄ .·▄▄▄▄  ·▄▄▄▄         ▐ ▄
██· █▌▐███▪▐█▐█ ▀█ ·██ ▐███▪▐█ ▀█ ▐█ ▀ ▪▀▄.▀·██▪ ██ ██▪ ██ ▪     •█▌▐█
██▪▐█▐▐▌██▀▐█▄█▀▀█ ▐█ ▌▐▌▐█·▄█▀▀█ ▄█ ▀█▄▐▀▀▪▄▐█· ▐█▌▐█· ▐█▌ ▄█▀▄ ▐█▐▐▌
▐█▌██▐█▌██▌▐▀▐█ ▪▐▌██ ██▌▐█▌▐█ ▪▐▌▐█▄▪▐█▐█▄▄▌██. ██ ██. ██ ▐█▌.▐▌██▐█▌
 ▀▀▀▀ ▀▪▀▀▀ · ▀  ▀ ▀▀  █▪▀▀▀ ▀  ▀ ·▀▀▀▀  ▀▀▀ ▀▀▀▀▀• ▀▀▀▀▀•  ▀█▄▀▪▀▀ █▪
"""

outro = """
▄▄▌ ▐ ▄▌ ▄ .▄ ▄▄▄· • ▌ ▄ ·.  ▄ .▄ ▄▄▄· ▄▄▌  ▄▄▌   ▄▄▄·
██· █▌▐███▪▐█▐█ ▀█ ·██ ▐███▪██▪▐█▐█ ▀█ ██•  ██•  ▐█ ▀█
██▪▐█▐▐▌██▀▐█▄█▀▀█ ▐█ ▌▐▌▐█·██▀▐█▄█▀▀█ ██▪  ██▪  ▄█▀▀█
▐█▌██▐█▌██▌▐▀▐█ ▪▐▌██ ██▌▐█▌██▌▐▀▐█ ▪▐▌▐█▌▐▌▐█▌▐▌▐█ ▪▐▌
 ▀▀▀▀ ▀▪▀▀▀ · ▀  ▀ ▀▀  █▪▀▀▀▀▀▀ · ▀  ▀ .▀▀▀ .▀▀▀  ▀  ▀
 """


@click.command()
@click.argument("number")
@click.option("--country", default="GB", help="Country number is from")
@click.option(
    "--track", default="Wham Last Christmas", help="Track search string for Spotify"
)
@click.option("--delay", default="none", type=click.Choice(["none", "short", "long"]))
def whamem(number, country, track, delay):
    click.clear()
    click.secho(intro, bg="magenta", fg="green")
    nexmo_client = nexmo.Client(
        application_id=os.environ["NEXMO_APPLICATION_ID"],
        private_key=os.environ["NEXMO_PRIVATE_KEY"],
        key=os.environ["NEXMO_API_KEY"],
        secret=os.environ["NEXMO_API_SECRET"],
    )

    e164_number = False
    wtf_e164_message = click.style(
        "View information on WTF E.164 is?", bg="magenta", fg="white"
    )
    try_number_again_message = click.style(
        "Want to try entering the number again?", bg="magenta", fg="white"
    )

    while e164_number == False:
        insight_response = nexmo_client.get_basic_number_insight(number=number)
        if insight_response["status"] == 3:
            insight_response = nexmo_client.get_basic_number_insight(
                number=number, country=country
            )

        if insight_response["status"] != 0:
            click.clear()
            click.secho(intro, bg="magenta", fg="green")
            click.secho(
                f"{number} does not appear to be a valid telephone number",
                bg="magenta",
                fg="white",
            )
            click.secho(
                "It might work if you enter it in the E.164 format",
                bg="magenta",
                fg="white",
            )

            if click.confirm(wtf_e164_message):
                click.launch(
                    "https://developer.nexmo.com/concepts/guides/glossary#e-164-format"
                )

            if click.confirm(try_number_again_message):
                number = click.prompt("Ok, give it to me in E.164 this time")
            else:
                raise click.BadArgumentUsage(
                    click.style(
                        f"{number} does not appear to be a valid number. Try entering it in the E.164 format",
                        bg="red",
                        fg="white",
                        bold=True,
                    )
                )
        else:
            e164_number = insight_response["international_format_number"]

    # We have a valid target number, let's get the track
    spotify_client_credentials_manager = SpotifyClientCredentials(
        client_id=os.environ["SPOTIFY_CLIENT_ID"],
        client_secret=os.environ["SPOTIFY_CLIENT_SECRET"],
    )
    spotify_client = spotipy.Spotify(
        client_credentials_manager=spotify_client_credentials_manager
    )
    tracks = spotify_client.search(track, limit=1, type="track")

    if len(tracks["tracks"]["items"]) == 0:
        raise click.BadOptionUsage(
            track,
            click.style(f"Can't find track: {track}", bg="red", fg="white", bold=True),
        )

    track = tracks["tracks"]["items"][0]

    # Start our local ngrok tunnel
    try:
        ngrok_tunnel = requests.post(
            "http://localhost:4040/api/tunnels",
            json={"addr": 8008, "proto": "http", "name": "pvpwham", "bind_tls": True},
        ).json()
    except requests.exceptions.ConnectionError:
        raise click.UsageError(
            click.style(
                "Please make sure ngrok is running", bg="red", fg="white", bold=True
            )
        )

    click.secho("## Starting the Call", bg="blue", fg="white", bold=True)
    nexmo_client.create_call(
        {
            "to": [{"type": "phone", "number": e164_number}],
            "from": {"type": "phone", "number": os.environ["NEXMO_VIRTUAL_NUMBER"]},
            "answer_url": [ngrok_tunnel["public_url"]],
            "event_url": [f"{ngrok_tunnel['public_url']}/events"],
        }
    )

    def quit_cherry():
        cherrypy.engine.exit()
        click.secho("## Exiting NCCO Server", bg="blue", fg="white", bold=True)
        requests.delete("http://localhost:4040/api/tunnels/pvpwham")
        click.secho("## Closing tunnel", bg="blue", fg="white", bold=True)

    def fetch_recording():
        data = cherrypy.request.json
        click.secho("## Fetching Call Recording", bg="green", fg="black", bold=True)
        recording_response = nexmo_client.get_recording(data["recording_url"])

        recordingfile = f"/tmp/{data['recording_uuid']}.mp3"
        os.makedirs(os.path.dirname(recordingfile), exist_ok=True)

        with open(recordingfile, "wb") as f:
            f.write(recording_response)

        click.secho("## Call Recording Saved", bg="green", fg="black", bold=True)
        if click.confirm(
            click.style(
                "## Listen to your friend's anguish now?", bg="magenta", fg="white"
            )
        ):
            click.launch(recordingfile)

    cherrypy.tools.quitcherry = cherrypy.Tool("on_end_request", quit_cherry)
    cherrypy.tools.fetch_recording = cherrypy.Tool("on_end_request", fetch_recording)

    @attr.s
    class NCCO(object):
        preview_url = attr.ib()
        ngrok_tunnel = attr.ib()

        @cherrypy.expose
        @cherrypy.tools.json_out()
        def index(self, **params):
            ncco_file = [
                {
                    "action": "record",
                    "eventUrl": [f"{self.ngrok_tunnel['public_url']}/recording"],
                }
            ]

            if delay == "short":
                ncco_file.append({"action": "talk", "text": "whamageddon"})
            elif delay == "long":
                ncco_file.append(
                    {
                        "action": "talk",
                        "text": "hang up your phone or prepare to enter Whamhalla",
                    }
                )

            ncco_file.append(
                {"action": "stream", "streamUrl": [f"{self.preview_url}?t=mp3"]}
            )

            return ncco_file

        @cherrypy.expose
        @cherrypy.tools.json_in()
        @cherrypy.tools.quitcherry()
        @cherrypy.tools.fetch_recording()
        def recording(self):
            click.secho("## Recording Ready", bg="green", fg="black", bold=True)
            return "OK"

        @cherrypy.expose
        @cherrypy.tools.json_in()
        def events(self):
            data = cherrypy.request.json
            click.secho(
                f"## Status: {data['status']}", bg="blue", fg="white", bold=True
            )
            return "OK"

    click.secho("## NCCO Server Ready", bg="blue", fg="white", bold=True)
    cherrypy.config.update({"server.socket_port": 8008, "environment": "embedded"})
    cherrypy.quickstart(
        NCCO(preview_url=track["preview_url"], ngrok_tunnel=ngrok_tunnel)
    )

    click.clear()
    click.secho(outro, bg="cyan", fg="green")

    click.secho(
        random.choice(
            [
                "You're a horrible person. Whamming complete",
                "Well done Krampus, you've just ruined your friend's Christmas",
                "You're totally getting coal in your stocking, consider them Wham'd",
                "May your Christmas Turkey be dry for what you've done to your friend.",
                "Your friend has been wham'd and you're on the naughty list",
            ]
        ),
        bg="red",
        fg="white",
        bold=True,
    )


if __name__ == "__main__":
    whamem()
