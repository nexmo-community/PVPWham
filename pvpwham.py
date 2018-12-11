import os
import random
import click
import attr
import requests
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import cherrypy
import nexmo


@click.command()
@click.argument("number")
@click.option("--country", default="GB", help="Country number is from")
def whamem(number, country):
    click.clear()
    nexmo_client = nexmo.Client(
        application_id=os.environ["NEXMO_APPLICATION_ID"],
        private_key=os.environ["NEXMO_PRIVATE_KEY"],
        key=os.environ["NEXMO_API_KEY"],
        secret=os.environ["NEXMO_API_SECRET"],
    )

    insight_response = nexmo_client.get_basic_number_insight(number=number)
    if insight_response["status"] == 3:
        insight_response = nexmo_client.get_basic_number_insight(
            number=number, country=country
        )

    if insight_response["status"] != 0:
        click.secho(
            "Invalid number, try supplying it in the international format",
            bg="red",
            fg="white",
            bold=True,
        )
        return 1
    else:
        # We have a valid target number, let's get the track
        spotify_client_credentials_manager = SpotifyClientCredentials(
            client_id=os.environ["SPOTIFY_CLIENT_ID"],
            client_secret=os.environ["SPOTIFY_CLIENT_SECRET"],
        )
        spotify_client = spotipy.Spotify(
            client_credentials_manager=spotify_client_credentials_manager
        )
        track = spotify_client.track("2FRnf9qhLbvw8fu4IBXx78")

        # Start our local ngrok tunnel
        try:
            ngrok_tunnel = requests.post(
                "http://localhost:4040/api/tunnels",
                json={
                    "addr": 8008,
                    "proto": "http",
                    "name": "pvpwham",
                    "bind_tls": True,
                },
            ).json()
        except requests.exceptions.ConnectionError:
            click.secho(
                "Please make sure ngrok is running", bg="red", fg="white", bold=True
            )
            return 1

        click.secho("Starting the call", bg="blue", fg="white")
        nexmo_client.create_call(
            {
                "to": [
                    {
                        "type": "phone",
                        "number": insight_response["international_format_number"],
                    }
                ],
                "from": {"type": "phone", "number": os.environ["NEXMO_VIRTUAL_NUMBER"]},
                "answer_url": [ngrok_tunnel["public_url"]],
            }
        )

        def quit_cherry():
            click.secho("Call answered", bg="cyan", fg="red", blink=True, bold=True)
            cherrypy.engine.exit()
            click.secho("Exiting NCCO server", bg="blue", fg="white")
            requests.delete("http://localhost:4040/api/tunnels/pvpwham")
            click.secho("Closing tunnel", bg="blue", fg="white")
            click.secho("Target has been Wham'd", bg="green", fg="black")

        cherrypy.tools.quitcherry = cherrypy.Tool("on_end_request", quit_cherry)

        @attr.s
        class NCCO(object):
            preview_url = attr.ib()

            @cherrypy.expose
            @cherrypy.tools.json_out()
            @cherrypy.tools.quitcherry()
            def index(self, **params):
                return [
                    {"action": "stream", "streamUrl": [f"{self.preview_url}?t=mp3"]}
                ]

        click.secho("NCCO server ready", bg="blue", fg="white")
        cherrypy.config.update({"server.socket_port": 8008, "environment": "embedded"})
        cherrypy.quickstart(NCCO(preview_url=track["preview_url"]))

    click.clear()
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
