-module(server).
-export([start/0]).

start() ->
    {ok, Listen} = gen_tcp:listen(38388,
                                  [list, {packet, 0},
                                   {reuseaddr, true},
                                   {active, false}]),
    {ok, Socket} = gen_tcp:accept(Listen),
    do_connection(Socket),
    ok = gen_tcp:close(Socket).


handle_tcp(Socket, Remote) ->
    case gen_tcp:recv(Socket, 0, 5000) of
        {ok, Data} ->
            gen_tcp:send(Remote, Data),
            handle_tcp(Remote, Socket);
        {error, closed} ->
            io:format("Closed~n");
        {error, timeout} ->
            io:format("Timeout~n"),
            handle_tcp(Remote, Socket)
    end.

do_connection(Socket) ->
    {ok, [Len]} = gen_tcp:recv(Socket, 1),
    {ok, Host} = gen_tcp:recv(Socket, Len),
    {ok, [H, L]} = gen_tcp:recv(Socket, 2),
    Port = H * 256 + L,
    {ok, Remote} = gen_tcp:connect(Host, Port,
                                   [{active, false},
                                    {reuseaddr, true},
                                    {send_timeout, 5000},
                                    {packet, 0}]),
    io:format("Connected to ~p:~p~n", [Host, Port]),
    handle_tcp(Socket, Remote).
