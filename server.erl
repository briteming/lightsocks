-module(server).
-export([start/0]).

get_left_value(S, Index, Result) ->
    case Index of
        8 ->
            Result;
        _ ->
            [H|T] = S,
            get_left_value(T, Index + 1, Result + (round(math:pow(256, Index)) * H))
    end.

ordering(X, Y, A, N) ->
    Left = A rem (X + N),
    Right = A rem (Y + N),
    Left =< Right.

sort_table(Table, _, 1024) ->
    Table;
sort_table(Table, A, N) ->
    Fun = fun(X, Y) -> ordering(X, Y, A, N) end,
    NewTable = lists:sort(Fun, Table),
    sort_table(NewTable, A, N + 1).

get_table(Key) ->
    Bin = crypto:md5(Key),
    S = binary:bin_to_list(Bin),
    A = get_left_value(S, 0, 0),
    Table = lists:seq(0, 255),
    sort_table(Table, A, 1).

setnth(1, [_|Rest], New) -> [New|Rest];
setnth(I, [E|Rest], New) -> [E|setnth(I-1, Rest, New)].

get_reverse_table(_, 257, Result) -> Result;
get_reverse_table(From, N, Result) ->
    Index = lists:nth(N, From),
    NewResult = setnth(Index + 1, Result, N - 1),
    get_reverse_table(From, N + 1, NewResult).

translate(S, D) ->
    [lists:nth(X + 1, D) || X <- S].

start() ->
    {ok, Listen} = gen_tcp:listen(38388,
                                  [list, {packet, 0},
                                   {reuseaddr, true},
                                   {active, false}]),
    ENC = get_table("the_secret_key"),
    DEC = get_reverse_table(ENC, 1, lists:seq(0, 255)),
    Encode = fun(S) -> translate(S, ENC) end,
    Decode = fun(S) -> translate(S, DEC) end,
    spawn(fun() -> par_connect(Listen, Encode, Decode) end).

par_connect(Listen, Encode, Decode) ->
    {ok, Socket} = gen_tcp:accept(Listen),
    spawn(fun() -> par_connect(Listen, Encode, Decode) end),
    do_connection(Socket, Encode, Decode),
    ok = gen_tcp:close(Socket).

%%
%% Some magic here:
%% Socket, Result == From, To
%% Node that Encode / Decode are also changeing
%%
handle_tcp(Socket, Remote, Encode, Decode) ->
    case gen_tcp:recv(Socket, 0, 1) of
        {ok, Data} ->
            gen_tcp:send(Remote, Decode(Data)),
            handle_tcp(Remote, Socket, Decode, Encode);
        {error, timeout} ->
            handle_tcp(Remote, Socket, Decode, Encode);
        {error, closed} ->
            ok
    end.

do_connection(Socket, Encode, Decode) ->
    {ok, [Len]} = gen_tcp:recv(Socket, 1),
    {ok, _Host} = gen_tcp:recv(Socket, Len),
    Host = Decode(_Host),
    {ok, [H, L]} = gen_tcp:recv(Socket, 2),
    Port = H * 256 + L,
    {ok, Remote} = gen_tcp:connect(Host, Port,
                                   [{active, false},
                                    {reuseaddr, true},
                                    {send_timeout, 5000},
                                    {packet, 0}]),
    io:format("Connected to ~p:~p~n", [Host, Port]),
    handle_tcp(Socket, Remote, Encode, Decode).
