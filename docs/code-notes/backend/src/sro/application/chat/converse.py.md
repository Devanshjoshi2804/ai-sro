# Notes for `backend/src/sro/application/chat/converse.py`

Comments and docstrings moved out of [`backend/src/sro/application/chat/converse.py`](../../../../../../../backend/src/sro/application/chat/converse.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/chat/converse.py#L1): Docstring

> Say something to the system, and get back what it worked out.
>
> The reply is never improvised. It is a rendering of a `Resolution`: the skill
> that was matched and what it still needs, the choice between two that were too
> close, or what the knowledge base knows about a task nobody has taught. The
> prose exists so an operator can read it; the decision is stored beside it so an
> auditor does not have to.
>
> **Nothing is performed here.** A matched skill is offered, and starting it is a
> separate request the operator makes — which is what makes their confirmation
> the authorisation an assisted run records.

## module, [line 1412](../../../../../../../backend/src/sro/application/chat/converse.py#L1412): Note on the line above

Code: `LOOKED = "looked"`

> The decision a lookup's answer rides on into the conversation.
>
> Its own kind, and not `note`: the panel draws it with `result()`, which counts
> the records and puts the first few in a table. A kind nobody recognises is a
> sentence, and a sentence about fifty records is the raw-JSON preview this
> replaced.

## module, [line 1415](../../../../../../../backend/src/sro/application/chat/converse.py#L1415): Note on the line above

Code: `K_RAN_OUT = ("timeout", "timed out", "deadline")`

> What the channel says when nobody answered in time. The extension's own
> words, matched here rather than translated -- `unreachable` is a browser that
> said no and this is one that said nothing, and they want different sentences.

## `_NotAsked`, [line 96](../../../../../../../backend/src/sro/application/chat/converse.py#L96): Docstring

> Nobody has placed this sentence against the jobs yet.
>
> A sentinel rather than `None`, because `None` is already an answer on this
> path -- it is what `_placed_by_the_rig` returns for a sentence that names
> no job, which is exactly the case that must not be confused with "not
> looked at".

## `_why_it_failed`, [line 1265](../../../../../../../backend/src/sro/application/chat/converse.py#L1265): Docstring

> Say what actually went wrong, in the words of the thing that went wrong.
>
> "1 step did not satisfy their post-conditions" is true of a skill that has
> drifted, a system that is down, and a session that has expired, and those
> want three different people to do three different things. The step already
> knows which; it was just not being read.

## `_what_happened`, [line 1279](../../../../../../../backend/src/sro/application/chat/converse.py#L1279): Docstring

> One line about a run, in the words of what it did.

## `_reply`, [line 1295](../../../../../../../backend/src/sro/application/chat/converse.py#L1295): Docstring

> What to say. Every branch says what happens next, because a reply that
> only reports a state leaves the operator to guess at the next move.

## `_last_time`, [line 1329](../../../../../../../backend/src/sro/application/chat/converse.py#L1329): Docstring

> What the demonstrations used, where that is all anybody has to go on.
>
> A parameter that exists because an operator asked to be prompted for it was
> a constant a moment ago, and saying what it was is the difference between a
> question somebody can answer and one they have to go and look up.

## `_what_it_found`, [line 1340](../../../../../../../backend/src/sro/application/chat/converse.py#L1340): Docstring

> What a composed read found, in the words of the question.

## `_derived`, [line 1352](../../../../../../../backend/src/sro/application/chat/converse.py#L1352): Docstring

> A composed read, as the console renders any other answer.
>
> Carried with where it came from: a request this system wrote is only
> trustworthy if the operator can see what it was built out of.

## `_decision`, [line 1368](../../../../../../../backend/src/sro/application/chat/converse.py#L1368): Docstring

> The structured half of the reply, kept for the audit trail.

## `_last_asked`, [line 1393](../../../../../../../backend/src/sro/application/chat/converse.py#L1393): Docstring

> The operator's previous sentence, which is where a follow-up's subject is.
>
> Theirs rather than the assistant's: the reply is full of words the system
> chose, and letting those steer the next match would have the console
> talking to itself.

## `_awaiting`, [line 1400](../../../../../../../backend/src/sro/application/chat/converse.py#L1400): Docstring

> The skill the last reply asked for values for, if it is still waiting.

## `_seen`, [line 1423](../../../../../../../backend/src/sro/application/chat/converse.py#L1423): Docstring

> One answer, in the shape every surface draws it from. See
> `application.lookup.answer.as_seen` -- the trimming is there so the card, the
> conversation and a model asked to read it all get the same answer.

## `_what_was_found`, [line 1435](../../../../../../../backend/src/sro/application/chat/converse.py#L1435): Docstring

> The sentence above the table, for a surface that draws no table.
>
> Deliberately thin. What the answer SAYS is in the records, and a sentence
> claiming to summarise them would be this system inventing a number: the
> table is the answer and this is its label.

## `_nothing_back`, [line 1453](../../../../../../../backend/src/sro/application/chat/converse.py#L1453): Docstring

> "Nothing back from them yet" -- where a mail is what is being waited on.
>
> Read off the thread rather than guessed: the last mail this conversation
> sent, and the fact that its answer has not arrived. The second half needs
> no checking. A reply that had been read would have filled the value, and
> this sentence is only ever written while the question is still standing.
>
> Empty for a question nobody was mailed about, which is most of them: a run
> that came up short in front of a person asks the person.

## `_the_way_out`, [line 1465](../../../../../../../backend/src/sro/application/chat/converse.py#L1465): Docstring

> How to be taken at your word, said where it is needed.
>
> Every re-ask happens because a reading refused to take a sentence as the
> value, and that reading is told to refuse when it is unsure -- which is
> the right default and leaves somebody who typed a real value with no move
> except typing it again and being refused again. `question` already names
> that loop as the thing this design must not be, for the length case. This
> is the same exit for the reading case: `asking.named_in` takes a value
> the person named themselves without asking anybody, and this is the only
> place they are ever told so.

## `_gathered`, [line 1470](../../../../../../../backend/src/sro/application/chat/converse.py#L1470): Docstring

> Every value established so far **for this skill**.
>
> Read back off the decisions rather than held in memory: the thread is what
> survives a restart, and an operator answering three questions over five
> minutes should not depend on a process staying up.
>
> Filtered by skill, which the docstring always claimed and the code never
> did: it merged the values from every decision in the thread, so a thread
> where somebody asked about suppliers and then went on to create a client
> carried the supplier's values into the client's parameters. Values arriving
> from somewhere the operator never typed them is the worst possible way for a
> write to be wrong -- it looks answered.
>
> Nothing is gathered when nothing is being waited on. A fresh sentence brings
> its own values; the thread's older ones belong to whatever they were for.

## `Converse.note`, [line 146](../../../../../../../backend/src/sro/application/chat/converse.py#L146): Docstring

> Write something into the thread that nobody asked a question for.
>
> A pursuit finishes minutes after the request that started it, in a
> background task, and its progress lives only in this process. What it
> did has to end up somewhere an operator can read tomorrow.
>
> Only into a thread its caller opened (`_opened_by_the_caller`): B's pursuit
> wrote its note and gestures into A's thread (S1 round 3). The route checks
> the same with `may_start` before anything is driven, so this is the last
> line, not the first.

## `Converse._carry_on`, [line 325](../../../../../../../backend/src/sro/application/chat/converse.py#L325): Docstring

> Everything this door does with a sentence that answers no question.
>
> The body of `execute` from the question check down, unchanged and
> named, so that a sentence which turned out NOT to be an answer can be
> handled the ordinary way rather than being dropped for not fitting a
> box it was never about.

## `Converse._still_wanted`, [line 434](../../../../../../../backend/src/sro/application/chat/converse.py#L434): Docstring

> The standing question, minus anything the job no longer asks for.
>
> A question stands until it is answered or the job is dropped, and that
> is right -- it is what stops an ordinary reply burying it. What it
> missed is that the JOB can change underneath it. A field the job
> demanded on Monday may be one the page never asked for, learnt as a
> parameter only because two demonstrations happened to vary it, and
> since 2026-09-22 no longer demanded at all.
>
> Measured on the deployment that day. `Department takes 10 characters.
> What should it be?` was asked at 11:35 and was still being re-asked at
> 13:50 -- two hours and four unrelated sentences later, under every one
> of them, for a field the job had stopped requiring in between. The
> operator asked for a new customer type, was offered one, and got the
> old question back under the offer. There is no answer that ends it
> except naming a value nobody needs, and no reason to.
>
> So the job's own declaration is read again here rather than trusted
> from when the question was written. It can only ever REMOVE names: a
> question is still a question about the job it named, and a field that
> has since become required is one the run will ask for itself.
>
> One read, and only where a question is standing. A thread with nothing
> waiting pays nothing.

## `Converse._question_stands`, [line 468](../../../../../../../backend/src/sro/application/chat/converse.py#L468): Docstring

> Whether a question is standing NOW, rather than when this request
> began.
>
> `execute` reads the thread once, at the top, and everything after that
> is a model call: the reading, the placement, the resolver. Seconds. And
> the question this door would talk over is written by somebody else --
> `RunWorkflow._ask_for_values` (`workflow_runs.py:589`), from a task the
> start-run route spawned and never awaited (`routers/workflow_runs.py:
> 139`), after a whole live browser run has tried and failed to find the
> values. Two independent transactions on one thread, no lock between
> them.
>
> Measured on the deployment 2026-09-22 at 01:06. The operator asked for
> a customer type, the run went to look in their mail, and they typed
> `i will type` while it was looking. This door had read the thread
> before the run's question was committed, so `pending_job` saw a job
> offer rather than a question, `standing` was false, and the guard below
> never fired: *"Nobody has demonstrated that, so I would work it out on
> the screen: i will type"*, and five Configuration menus. The question
> landed a moment later and was buried under them -- which is why the
> stored thread has the question at 20 and the plan at 22.
>
> So the freshest possible read, at the last possible moment, and only on
> the path that is about to say the one thing worth not saying. It does
> not close the window -- an operator who types before the run has asked
> anything still meets a thread with no question in it -- and that
> remainder is the run's own flight, not this read. What it does close is
> every case where the question was already written by the time this door
> decided, which is the case that was measured.

## `Converse._also_said`, [line 473](../../../../../../../backend/src/sro/application/chat/converse.py#L473): Docstring

> Write down what they said, without acting on it.
>
> The sentence is theirs and it was said: a conversation that answers a
> person without showing what they asked reads, a minute later, as the
> system talking to itself.

## `Converse._ask_it_again`, [line 488](../../../../../../../backend/src/sro/application/chat/converse.py#L488): Docstring

> Put the standing question back, under whatever was just said.
>
> The same decision it was asked with, so the state rides along intact --
> what is established, what is still missing, where the run had got to.
> A question re-asked with a thinner decision than the one it replaces is
> a question that loses an answer somebody already gave.

## `Converse._is_it_an_answer`, [line 527](../../../../../../../backend/src/sro/application/chat/converse.py#L527): Docstring

> The value to take, or None where that sentence was not an answer.
>
> Never None where nothing could read it. A deployment with no model, a
> reading that raised, a cap spent -- all of them behave as this door
> behaved before the reading existed, because a panel that quietly stops
> accepting answers when a model is unreachable is worse than one that
> takes too many.
>
> `let_go` first and without asking anybody: "no" and "never mind" end
> the question, and a reading asked whether "no" answers "what should
> Customer Type be" has been given a question with no good answer.

## `Converse._answer_the_question`, [line 546](../../../../../../../backend/src/sro/application/chat/converse.py#L546): Docstring

> Take that sentence as the value it was asked for, and go on.
>
> Three ends, and the whole state of it lives on the decision each one
> writes -- not in a session, not on a row. An operator answering two
> questions over five minutes does not depend on a process staying up,
> and a second browser reading the thread sees the same thing.
>
> **Called off.** "No", "never mind": said whole, never by substring, so
> a description reading "leave it in receiving" is a description.
>
> **One down, more to go.** The answer goes in, the next question comes
> out, and the decision carries what is established so far.
>
> **The last one.** No more questions: the run is started here
> (`_start_it`), and the thread says "Running" with the run's id -- no
> second confirmation. They already said yes; asking twice for the same
> permission is how a system teaches somebody to stop reading what it asks.

## `Converse._say_yes_to_it`, [line 583](../../../../../../../backend/src/sro/application/chat/converse.py#L583): Docstring

> Start the job that was just offered, or ask for what it still needs.
>
> Two ends, and which one is decided by whether anything can go and look.
> A deployment that can read the operator's mail starts the job and lets
> the run find the rest -- that is what the card's own Yes does, and a
> conversation that demanded values the card would not is two answers to
> one question. A deployment that cannot asks here, one value at a time,
> and `_answer_the_question` takes it from there.

## `Converse._placed_by_the_rig`, [line 792](../../../../../../../backend/src/sro/application/chat/converse.py#L792): Docstring

> Which mined job this sentence is about, or None to ask the skills.
>
> None on every refusal as well as on a sentence the rig cannot place:
> no model configured, the day's cap spent, a door that raised. The
> conversation still happens -- it happens the way it did before this
> existed, which is the behaviour the console has always had.

## `Converse._say_the_job`, [line 802](../../../../../../../backend/src/sro/application/chat/converse.py#L802): Docstring

> The rig's answer, in the thread, with what a press would need.

## `Converse._ask_which`, [line 877](../../../../../../../backend/src/sro/application/chat/converse.py#L877): Docstring

> A question with the jobs it was choosing between, and no press.
>
> `kind: "which_job"` and deliberately not `"job"`: the browser builds an
> offer out of a job decision, and a decision it cannot act on must not
> look like one it can.

## `Converse.matched`, [line 915](../../../../../../../backend/src/sro/application/chat/converse.py#L915): Docstring

> A watched mailbox recognised a task. Said once, by name.
>
> A skill or a mined job: `named` is what the person reads and the two
> ids say which kind it was, because the press that follows goes to a
> different door for each. One method rather than two -- the sentence,
> the once-per-offer rule and the "names, never values" rule are the same
> for both, and a second copy of them is two that drift.
>
> The operator has to see this somewhere that survives the panel closing,
> which is the thread. What must not follow it there are the values: they
> were read out of somebody's mail, and `ValueAt` exists so they stay in
> the browser that read them. So the message carries which names were
> read and not what they said. The browser still holds the values, and
> the press that starts a run carries them then.
>
> Once per offer. A browser reports a match per frame it sees the mail in,
> and a conversation that says the same sentence four times is one nobody
> reads. Recognised by the offer id the browser minted -- absent from an
> older extension, which is why nothing is written without one: there
> would be no way to tell the second report from the first.

## `Converse._said_to_a_run`, [line 956](../../../../../../../backend/src/sro/application/chat/converse.py#L956): Docstring

> Something said to a run that is happening, rather than a request.
>
> Only by the run's starter, in a thread they opened (invariant 5; S1 round
> 1); anything else is a 409 and nothing is written. The opener half is
> `_opened_by_the_caller`, the same rule `started` keeps. `last_run` reads a run id
> off any message, so a note is how a run gets into a thread's status line:
> unchecked, B put B's run into A's thread and `_what_stands` let B past the
> offer gate there.
>
> Not `note` above, which is this class's other way of writing into a
> thread: that one is the system reporting a pursuit that finished in the
> background, and this one is the operator talking. Two methods of one
> name meaning opposite halves of an exchange is a trap for whoever reads
> them next.
>
> Kept and not resolved. An operator watching a run who types "use the
> north yard address" is talking about the thing in front of them; putting
> that sentence through intent matching finds some other skill and offers
> to run it, which is the opposite of what they meant.
>
> Nothing acts on it yet. It is recorded against the run so it is in the
> transcript beside the step it arrived during, and so the surface can say
> honestly that it was heard -- what reads it is the planner, when there
> is one. A note that silently changed a run would be worse than one that
> does nothing: changing the values a run uses is `Run.revise`'s job, where
> the change is checked against the names the skill declares.

## `Converse.may_start`, [line 977](../../../../../../../backend/src/sro/application/chat/converse.py#L977): Docstring

> Whether the caller may start a run into this thread, asked by the route
> before `durable.execute_skill`: a refusal after the run started would leave
> a run going that no thread shows (S1 round 2).

## `Converse.started`, [line 981](../../../../../../../backend/src/sro/application/chat/converse.py#L981): Docstring

> Put a run into the conversation the moment it starts.
>
> Before, the message was written when the run finished, so a task that
> takes twelve seconds left the operator with a spinner and a card that
> forgot what it was doing. The message is the anchor: the console
> streams the steps into it as they land, and it is already in the
> transcript if the browser is closed halfway.

## `Converse.performed`, [line 1018](../../../../../../../backend/src/sro/application/chat/converse.py#L1018): Docstring

> Write a run the operator started into the conversation that asked for it.
>
> Until now a run started from a card lived in the console's memory: it
> survived nothing -- a re-render put the empty form back, and a reload
> lost the fact that anything had happened at all. A run belongs in the
> transcript for the same reason every other decision does. Somebody
> reading this thread tomorrow needs to see that a supplier was created,
> by whom, and what came back.

## `Converse._narrowed`, [line 1058](../../../../../../../backend/src/sro/application/chat/converse.py#L1058): Docstring

> The question that was actually asked, where the taught skill answers
> a wider one.
>
> "Show me supplier TESTSUPPLIERSRO" matched the read that lists every
> supplier, and replaying it returned all two hundred and thirty-nine --
> the one word that said which supplier was dropped on the floor. Here
> the field dictionary says what that value is called, the taught call
> proves the filter dialect, and the request is composed from both.

## `Converse._next_steps`, [line 1090](../../../../../../../backend/src/sro/application/chat/converse.py#L1090): Docstring

> What can be asked next, from what this answer actually contains.

## `Converse._write_down`, [line 1118](../../../../../../../backend/src/sro/application/chat/converse.py#L1118): Docstring

> Keep the question, so answering it once teaches it for everybody.
>
> The next person to ask about "parcel" gets a narrowed read rather than
> the same question, because what an operator says a word means is
> knowledge like anything else here.

## `Converse._look_it_up`, [line 1132](../../../../../../../backend/src/sro/application/chat/converse.py#L1132): Docstring

> The lookup door's answer to this question, or None if it is not one.
>
> None on every path that is not "a question with no skill behind it":
> a sentence that asks for work, a question a taught skill matched, a
> deployment with no lookup services, a plan that came back unready.
> Each of those falls through to what this door did before, which is
> still the right answer for them.

## `Converse._say_what_was_found`, [line 1148](../../../../../../../backend/src/sro/application/chat/converse.py#L1148): Docstring

> The answer, in the thread, carried as structure rather than prose.
>
> The panel already has the renderer: `result.js` reads a body, counts
> the records and draws the first few in a table. What it could not do
> was reach one -- a lookup's answer arrived only through `/v1/ask`, into
> a card beside the conversation, while the conversation itself carried
> the screen walk. So the decision carries the same shape that card is
> built from and the thread draws it the same way.

## `Converse._answer_now`, [line 1179](../../../../../../../backend/src/sro/application/chat/converse.py#L1179): Docstring

> Run a read the moment it is asked for, and answer with what came back.

## `Converse.__init__`, [line 131](../../../../../../../backend/src/sro/application/chat/converse.py#L131): Comment

Code: `self._answers = answers`

> Whether a sentence typed while a question stands is the answer to it.
> Optional: a deployment without one takes every sentence, exactly as
> this door did before the reading existed.

## `Converse.__init__`, [line 139](../../../../../../../backend/src/sro/application/chat/converse.py#L139): Comment

Code: `self._can_gather = can_gather`

> Whether a run of a mined job can go and find a value nobody typed.
>
> What the card asks for, and it is the difference between a person
> being asked to type a code out of a mail they have open and a run
> reading it themselves. Told to the panel rather than decided there:
> the connector is a deployment's, and a browser cannot know whether
> this one has a mailbox it may read.

## `Converse.__init__`, [line 140](../../../../../../../backend/src/sro/application/chat/converse.py#L140): Comment

Code: `self._plan_lookups = plan_lookups`

> The door that owns a question.
>
> `/v1/ask` has always decided which of the two worlds a sentence
> belongs to -- an instruction for the jobs, a question for the
> lookups -- and this door never asked. So a question nothing was
> taught for came back here as a PROPOSAL to open five screens and
> work it out, seven seconds before the lookup door answered it
> properly from an endpoint. Two answers on screen to one sentence,
> and the wrong one first.
>
> Optional, like every other model-backed service here: a deployment
> without one behaves exactly as this door did before.

## `Converse.execute`, [line 173](../../../../../../../backend/src/sro/application/chat/converse.py#L173): Comment

Code: `async with self._uow as uow:`

> A question this conversation asked is answered by the next thing
> said in it, before anything tries to read that sentence as a fresh
> request.
>
> "GPP" placed against the jobs is a sentence about nothing. Against
> the question that was actually asked -- *what should Customer Type
> be?* -- it is the answer, and reading it any other way is how a
> system asks somebody a question and then ignores what they say. It
> also saves the model call: the reading that matters already happened
> when the job was placed.

## `Converse.execute`, [line 199](../../../../../../../backend/src/sro/application/chat/converse.py#L199): Comment

Code: `answered_it, about = await self._is_it_an_answer(ctx, waiting, text)`

> And only if it IS one. A question standing here used to take
> whatever was typed next, which is right for `GU9` and wrong for
> everything else somebody types while they wait -- and what they
> type while waiting is usually about the waiting.
>
> Measured on the deployment 2026-09-18: the operator had sent the
> answer by mail and typed `has reply arrived` to ask this system
> whether it had landed. It was taken as the value, a run started a
> millisecond later, and `HAS REPLY ARRIVED` went into a
> four-character box in a live warehouse system.
>
> A sentence that is not an answer falls through to everything
> below and is treated as what it is. The question is not consumed,
> so it is still standing when they do answer it.

## `Converse.execute`, [line 209](../../../../../../../backend/src/sro/application/chat/converse.py#L209): Comment

Code: `if about != "another_task":`

> About the waiting, which is what a person who is waiting asks
> about. Answered here and not handed on.
>
> `check now` went to the task resolver, which is a door for "what
> work do you want done" -- so it planned one, and answered two
> words about a mailbox with a wall of text about Check In and
> Check Out screens nobody had mentioned. Seen on the deployment
> 2026-09-18, 16:42.

## `Converse.execute`, [line 218](../../../../../../../backend/src/sro/application/chat/converse.py#L218): Comment

Code: `placed = await self._placed_by_the_rig(ctx, text)`

> And only where the jobs agree that it IS one.
>
> `another_task` is a model's reading of a sentence, and the
> sentence that named this was `i wll type` -- the operator saying
> they would type the value, in answer to a question asking for
> it. Read as a request for different work, it went to the door
> that proposes work: "Nobody has demonstrated that, so I would
> work it out on the screen: i wll type", and five Configuration
> menus nobody had mentioned. Measured on the deployment
> 2026-09-21 at 17:10, in an operator's own conversation.
>
> The reading was wrong and no wording will make it always right.
>
> Refusing to carry on at all is not the answer either. Whether a
> sentence is a request for different work cannot be decided from
> the sentence -- "create an equipment type instead" places against
> nothing on a tenant that has never demonstrated one, and it is
> still a request. The door's own test says so: *somebody who says
> "create an equipment type instead" has asked for work, and a door
> that replied "I am still waiting on Customer Type" to that would
> be the old swallowing with better manners*.
>
> What CAN be decided is whether there is anything to say. The harm
> measured was not the carrying on; it was the PROPOSAL -- a door
> with no taught skill, no lookup and no read still answering, out
> of a plan it made from the screen. So the sentence is carried on
> with (`standing`), and where all this door has for it is a plan
> made up on the spot, it says nothing and the standing question is
> what the operator sees.
>
> The placement is handed down, so this costs no extra model call
> on the path that does turn out to be another task.

## `Converse.execute`, [line 219](../../../../../../../backend/src/sro/application/chat/converse.py#L219): Comment

Code: `await self._carry_on(`

> Said, answered, and then asked again.
>
> The asking again is not politeness. `pending_job` reads the LAST
> thing the assistant decided, so an ordinary reply written under a
> standing question buries it -- the sentence gets its answer and
> the question is gone, which is the same swallowing by a longer
> road. Repeating it is also what a person does: they answer what
> they were asked, and then say what they are still waiting for.

## `Converse._carry_on`, [line 339](../../../../../../../backend/src/sro/application/chat/converse.py#L339): Comment

Code: `offered = offered_job(said_before, answering)`

> And a job this conversation has just offered, agreed to.
>
> Measured on the deployment, 2026-09-17 at 03:17. The assistant said
> "Create a Customer Type does that -- say the word and I will run it",
> the operator said "pls do", and the reply was "Nothing has been
> taught for that": the sentence went to the resolver below, which
> ranks this tenant's taught SKILLS and had never heard of it. Nothing
> was holding on to what had just been offered.
>
> A system that asks for a word and then does not know the word is the
> same fault as the boxes on the offer card: it asks, and then ignores
> the answer.

## `Converse._carry_on`, [line 357](../../../../../../../backend/src/sro/application/chat/converse.py#L357): Comment

Code: `if isinstance(placed, _NotAsked):`

> The rig's jobs first, and where they place the sentence, only them.
>
> An operator typed "lets create warehouse equipment type" at a browser
> whose rig holds exactly that job, and was answered "Create a customer
> type does that. I still need long_description." The resolver below
> ranks the tenant's taught SKILLS -- seven of them, none about
> equipment types -- so it answered with the nearest thing it had. The
> right job was in the rig all along and this door never asked it.
>
> One model call and not two: the reading that answers here is the
> reading the panel's offer is built from, rather than this door
> spending one on the skills library and the browser spending another
> on the jobs.
> Asked here, unless the caller has already asked. A sentence typed
> under a standing question is placed against the jobs BEFORE the
> question is abandoned, and asking a second time would be a second
> model call for an answer this already has.

## `Converse._carry_on`, [line 376](../../../../../../../backend/src/sro/application/chat/converse.py#L376): Comment

Code: `parameters={**_gathered(thread, _awaiting(thread)), **(parameters or {})},`

> Values already given for the skill under discussion. An operator
> who answers one question at a time should not lose the first
> answer when they give the second.

## `Converse._carry_on`, [line 377](../../../../../../../backend/src/sro/application/chat/converse.py#L377): Comment

Code: `after=_last_asked(thread),`

> What was being talked about a moment ago. A conversation whose
> every sentence is resolved alone is not a conversation.

## `Converse._carry_on`, [line 382](../../../../../../../backend/src/sro/application/chat/converse.py#L382): Comment

Code: `looked = await self._look_it_up(ctx, text, resolution)`

> A question nothing was taught for belongs to the lookup door.
>
> The taught path below still comes first -- a skill that knows which
> call answers a question is a better answer than a plan made from the
> knowledge base. This is the case where there is no such skill, and
> where this door used to answer with a PROPOSAL: "Nobody has
> demonstrated reading that, so I will work it out on the screen",
> followed by five screens to open.
>
> Measured on the deployment 2026-09-21. Asked "is there a customer
> type called KKYT", three doors answered one sentence:
>
>   18:30:26  POST /v1/lookups            3601ms
>   18:30:35  POST /v1/threads/../messages 7691ms  <- the screen walk
>   18:30:43  POST /v1/ask                 6567ms  <- the answer
>
> The wrong one arrived first and read as final. The lookup planned
> `call /data/WM/wm/customerTypes`, got 200, and found KKYT -- which
> this door proposed to go and read off a screen instead.
>
> `is_a_question` is the same word rule `/v1/ask` decides by, with no
> model, so the two doors cannot disagree about what a question is.

## `Converse._carry_on`, [line 391](../../../../../../../backend/src/sro/application/chat/converse.py#L391): Comment

Code: `narrowed = await self._narrowed(ctx, resolution)`

> A question is answered from the system, now. The taught skill knows
> which call answers it; what it saw when it was taught is a description
> of that afternoon, and showing it as though it were current is how a
> console tells somebody there are sixteen when there are twenty-three.
>
> Only reads, and only when nothing is missing. A write still waits for
> the operator to say go -- that confirmation is what an assisted run
> records as its authorisation, and it is not ours to assume.
> The narrower question first, where the sentence asked one: replaying
> a taught read that answers something wider is how "show me supplier
> X" came back as every supplier there is.

## `Converse._carry_on`, [line 392](../../../../../../../backend/src/sro/application/chat/converse.py#L392): Comment

Code: `run = None if narrowed else await self._answer_now(ctx, resolution)`

> A question of our own stops the wider read too: answering something
> nobody asked, because the thing they did ask could not be placed, is
> the confident wrong answer wearing a table.

## `Converse._carry_on`, [line 394](../../../../../../../backend/src/sro/application/chat/converse.py#L394): Comment

Code: `if resolution.proposal is not None and (`

> A plan made up on the screen, under a question of ours that is still
> standing. This is the one thing this door says that is worth not
> saying: "Nobody has demonstrated that, so I would work it out on the
> screen: i wll type", and five Configuration menus nobody mentioned.
>
> Only the PROPOSAL. A taught skill still answers, a lookup still
> answers, and so does "Nothing has been taught for that" -- somebody
> who asks for work this tenant has never demonstrated is owed that
> sentence, not a second copy of the question they are already looking
> at. What they are not owed is a plan this door invented because it
> had nothing.

## `Converse._still_wanted`, [line 442](../../../../../../../backend/src/sro/application/chat/converse.py#L442): Comment

Code: `if job is None or not job.parameters:`

> A job that declares nothing has said nothing, which is not the same
> as saying nothing is required. A parameter is learnt from two doings
> that varied a field, so a job done once declares none at all -- and
> dropping its questions on that basis would silence every question a
> young job ever asks.

## `Converse._still_wanted`, [line 448](../../../../../../../backend/src/sro/application/chat/converse.py#L448): Comment

Code: `return replace(waiting, missing=still, known=known) if still else None`

> The job's field classes (C2's `field_classes`, from the job alone) and
> R2's aliases ride on the waiting ask as `known`, so a field named in the
> reply resolves through `request.field_of` exactly as the request reader
> resolves it (F1 round 1, I1). Never written to a decision.
>
> Nothing left to ask. The question is over, and the sentence under it
> is an ordinary sentence rather than an answer to something nobody
> needs.

## `Converse._is_it_an_answer`, [line 532](../../../../../../../backend/src/sro/application/chat/converse.py#L532): Comment

Code: `if named_in(pending, text):`

> Named by the person themselves, and nothing needs to be read.
>
> "Customer Type: RRF, Department: D1", or "i dont have manufature"
> (`asking.named_in`): the whole sentence goes to `answered`, which takes
> every named value in one reply and drops every field said not to be had
> (F1). Before F1 only `asking_for: value` was recognised, and the rest of
> a reply naming two fields rode into the first one's value.
>
> This is the way out of the loop. The reading is told to refuse when
> it is unsure, which is the right default and leaves an operator who
> typed a real value with no move except typing it again -- so the
> re-ask below tells them this form exists, and this takes it.

## `Converse._is_it_an_answer`, [line 544](../../../../../../../backend/src/sro/application/chat/converse.py#L544): Comment

Code: `return None, read.about`

> Could not tell is its own thing, not a reading that said `another_task`.
> `read.answers` is `None` on every path nothing could actually read -- no
> model, a call that raised, a reply with nothing in it -- and `read.about`
> is `""` on every one of them, which `if about != "another_task":` in
> `execute` reads as `the_wait` does: re-ask under the standing question,
> never carry on as though a sentence had been placed against the jobs.
> Taking the unreadable sentence as the value is how `HAS REPLY ARRIVED`
> reached a four-character box; this is the same question asked in
> reverse, at the door that decides what a refusal means.

## `_not_yet`, [line 1216](../../../../../../../backend/src/sro/application/chat/converse.py#L1216): Comment

Code: `refused = too_long_for(pending, text)`

> An answer the box will not hold leaves the question standing,
> and saying so is the whole difference between a loop somebody
> can get out of and one they cannot. Silently re-asking the
> same question reads as a system that ignored them.

## `_to_run`, [line 1256](../../../../../../../backend/src/sro/application/chat/converse.py#L1256): Comment

Code: `"from_step": job.from_step,`

> Where the run that asked had got to. The start is handed it as `from_step`
> and no `matched`, so the run begins there and does not re-walk every step
> the first run performed. (`matched` counts gestures a browser tail matched;
> the panel used to send `matched: 0`, which `resumes_at` turned back into
> step 0 -- the re-walk this was meant to prevent.)

## `_to_run`, [line 1257](../../../../../../../backend/src/sro/application/chat/converse.py#L1257): Comment

Code: `"mail_thread": job.mail_thread,`

> So the run this answer starts answers to the same mail a run the card
> started would have: it is the start's `conversation`.

## `Converse._say_the_job`, [line 809](../../../../../../../backend/src/sro/application/chat/converse.py#L809): Comment

Code: `if not placed.sure:`

> Not sure which job: ask, rather than start one.
>
> The reading is still the best one it had, and it is offered
> first -- but as a question with the others beside it, and with no
> `workflow_id` for a press to act on. A guess that creates one
> wrong record is a nuisance; the same guess against a list of
> twenty is twenty wrong records in a warehouse, and the cost of
> asking is one sentence.

## `Converse._say_the_job`, [line 820](../../../../../../../backend/src/sro/application/chat/converse.py#L820): Comment

Code: `if placed.cannot_run:`

> A job that cannot run is named with its reasons, as a note and not a job card
> whose press the start would refuse. Never "no such job".

## `Converse._say_the_job`, [line 821](../../../../../../../backend/src/sro/application/chat/converse.py#L821): Comment

Code: `said = (`

> The run goes and looks. Said as what will happen rather than
> as a demand, because the demand was the old behaviour and it
> put a person in front of four boxes -- two of them the body
> keys a form posts, which nobody has ever typed -- for values
> sitting in the mail that asked for the job.

## `Converse._say_the_job`, [line 856](../../../../../../../backend/src/sro/application/chat/converse.py#L856): Comment

Code: `decision={`

> The structured half, which is what a press is built from:
> the browser makes its offer out of this rather than
> spending a second reading of the same sentence.

## `Converse._say_the_job`, [line 869](../../../../../../../backend/src/sro/application/chat/converse.py#L869): Comment

Code: `"can_find": self._can_gather,`

> Whether the missing ones are a demand or a plan. The
> panel draws its boxes off this: required where
> nothing can go and look, optional where something
> can, and a blank that reaches the door is refused as
> a typed blank either way.

## `Converse._ask_which`, [line 907](../../../../../../../backend/src/sro/application/chat/converse.py#L907): Comment

Code: `"titles": titles,`

> The names, because the question is asked of a person:
> a panel drawing two buttons reading `wfl_c79d02bb`
> asks nobody anything.

## `Converse.matched`, [line 948](../../../../../../../backend/src/sro/application/chat/converse.py#L948): Comment

Code: `"missing": list(missing),`

> Where nothing can go and look, this is what the card
> says it cannot run without. Where something can, the
> names are still said -- a person reading the thread
> should know which values the mail did not carry --
> and `can_find` is what decides whether the button is
> a demand or a plan.

## `Converse.performed`, [line 1036](../../../../../../../backend/src/sro/application/chat/converse.py#L1036): Comment

Code: `"next": ("open" if any(step.unreachable for step in run.steps) else "ask")`

> The one thing that would help, for a surface that
> shows a failure as a sentence and a single button.
> A step nothing could reach is a page to open; every
> other failure is somebody's to look at.

## `Converse._narrowed`, [line 1074](../../../../../../../backend/src/sro/application/chat/converse.py#L1074): Comment

Code: `verb=resolution.verb,`

> The verb is what they want done, not a value to filter by:
> "count the addresses" asked which field the word "count" names,
> because two fields are called Count something.

## `Converse._narrowed`, [line 1079](../../../../../../../backend/src/sro/application/chat/converse.py#L1079): Comment

Code: `if narrowed.options:`

> Only a real choice becomes a question. A statement that this read
> cannot answer the sentence is not something to ask anybody.

## `Converse._narrowed`, [line 1086](../../../../../../../backend/src/sro/application/chat/converse.py#L1086): Comment

Code: `logger.info("the narrowed read did not answer: %s", asked.detail)`

> The narrowing was right and the request did not work -- an
> expired session, an endpoint that answered nothing. Falling back
> to the taught read answers a wider question, but answering
> nothing at all because a composed request failed is worse.

## `Converse._look_it_up`, [line 1136](../../../../../../../backend/src/sro/application/chat/converse.py#L1136): Comment

Code: `return None`

> Nothing here knows how to look it up, which is the case the
> proposal below is genuinely for: it says what the knowledge base
> has and offers to work the screen out once.

## `Converse._look_it_up`, [line 1146](../../../../../../../backend/src/sro/application/chat/converse.py#L1146): Comment

Code: `return await self._run_lookups.execute(ctx, plan=planned.plan, within=K_WHILE_TALKING)`

> `K_WHILE_TALKING`, not the lookup door's own budget. A reply in a
> panel is a turn in a conversation, and a turn that takes a minute has
> stopped being one: measured on the deployment 2026-09-21, request
> `req_10d3ff9b`, the browser's socket dropped twice inside one
> request, a command waited out the full 45 seconds, and the reply took
> 67459ms. Routing the conversation through this door is what made a
> thread reply wait on a browser at all; this is what stops it waiting
> on one that is not answering.

## `Converse._answer_now`, [line 1198](../../../../../../../backend/src/sro/application/chat/converse.py#L1198): Comment

Code: `logger.info("could not answer from the system: %s", refusal)`

> A refused read is worth saying out loud, and worth saying in the
> reply rather than as an empty answer: the breaker being open is a
> fact about the system, not an absence of transport modes.

## `_reply`, [line 1300](../../../../../../../backend/src/sro/application/chat/converse.py#L1300): Comment

Code: `wanted = ", ".join(resolution.missing_parameters)`

> Values were read, but not all of them. Telling somebody to "say
> go" when the run cannot start is how a system trains people to
> ignore what it says.

## `_decision`, [line 1382](../../../../../../../backend/src/sro/application/chat/converse.py#L1382): Comment

Code: `"items": [dict(item) for item in resolution.items],`

> The table the operator confirms. Rendered rather than acted on: their
> confirmation is what an assisted run records as its authorisation.

## `_decision`, [line 1384](../../../../../../../backend/src/sro/application/chat/converse.py#L1384): Comment

Code: `"suggestions": list(suggestions),`

> Earned from this answer's own columns and the skills taught for this
> entity. Never a fixed list: the console used to offer "which X are
> used for parcel" under every result in the system.

## `_decision`, [line 1387](../../../../../../../backend/src/sro/application/chat/converse.py#L1387): Comment

Code: `"run_id": run.id.value if run else None,`

> The answer, from the system, at the moment it was asked.

## `_decision`, [line 1388](../../../../../../../backend/src/sro/application/chat/converse.py#L1388): Comment

Code: `"matched_skill_name": resolution.matched.skill.name if resolution.matched else None,`

> The name, not only the id: a sidebar reading "ran skl_a6f7b33c" tells
> nobody anything.

## `_what_was_found`, [line 1439](../../../../../../../backend/src/sro/application/chat/converse.py#L1439): Comment

Code: `if any(_ran_out(one.detail) for one in found.looked):`

> Name the browser where the browser is what did not answer. "I could
> not read that. timeout" is a sentence about this system's plumbing;
> the person reading it can see their own browser and can do something
> about it.

## `_what_was_found`, [line 1442](../../../../../../../backend/src/sro/application/chat/converse.py#L1442): Comment

Code: `said = [`

> The reader's own sentence, where it read records.
>
> `Answer.sentence` is deterministic -- counted and named from the payload,
> never summarised by a model, because "16" has to be 16 -- and it is the
> line somebody asking a question wanted instead of a table. "Read from
> /data/WM/wm/customerTypes" was this door describing its own plumbing.

## `Converse._say_yes_to_it`, [line 610](../../../../../../../backend/src/sro/application/chat/converse.py#L610): Note

Code: `said = f"Left {offered.title}."`

> "No" to an offered job leaves it, as it drops a standing question: the
> offer stops standing and nothing runs. Without it the word went to the
> resolver as a request of its own.

## `Converse.execute`, [line 193](../../../../../../../backend/src/sro/application/chat/converse.py#L193): Note

Code: `and offered_job(said_before, answering) is None`

> An answer pressed under a question that is no longer open, or that is not a
> question at all, is refused with a reply and nothing else. It never falls
> through to the resolver or to another offer.

## `K_CLOSED`, [line 72](../../../../../../../backend/src/sro/application/chat/converse.py#L72): Note

Code: `K_CLOSED = "That question is no longer open, so nothing was done."`

> Said with no decision, so the refusal does not itself become the newest
> decision a typed sentence would be read against.

## `Converse.execute`, [line 177](../../../../../../../backend/src/sro/application/chat/converse.py#L177): Note

Code: `_opened_by_the_caller(ctx, before)`

> A thread belongs to its opener (invariant 5). Threads are readable across
> the tenant, and a should-we question carries the operator's own mail to
> colleagues; a colleague who can see it cannot act in it.
>
> Anybody but the opener is refused on every path, whatever stands (S1 round
> 3). Round 0 let a colleague on into `_carry_on` with nothing standing, and
> their request wrote an offer of their own into the opener's empty thread;
> earlier rounds checked only while a question or an offer stood, and a
> colleague's "GGD" under the opener's question was taken as its answer, a
> "yes" under an offer ran it.
>
> The refused caller is told, and nothing is written: the reply is added to
> the thread this request read and returned, never saved. They are told
> `_what_stands`' line when it has one -- for them that can only be a run they
> started (F2's status line, read-only) -- and otherwise that it was asked of
> somebody else. No rig, no resolver, no answer reader reads what they said.
>
> `opened_by` never changes, so this one read decides for the whole request:
> an offer that lands after it cannot let the colleague in further down.
>
> Chat never answers a run's own question (`run_asks`); that is the
> workflow-runs route, which checks the run's starter itself.

## `Converse._say_yes_to_it`, [line 598](../../../../../../../backend/src/sro/application/chat/converse.py#L598): Note

Code: `if still is None or still.id != asked:`

> The compare-and-set. The question was found open in one transaction and is
> answered in another; under the thread's row lock this checks it is still the
> open one before writing, so of two presses (or a press and a typed yes)
> exactly one answers and the other is told it is no longer open. The same
> check guards `_answer_the_question`.

## `_offer_of`, [line 1242](../../../../../../../backend/src/sro/application/chat/converse.py#L1242): Docstring

> The offer a yes or an answer is about: the `offer` its question carries,
> else the question itself. It is the start's `offer`, so the store refuses
> a second run of it however the second start arrives: a second panel, an
> older extension's own press, a mail read again after a crash. A question
> about a mail carries the mail as its offer (`mail:{id}`), and so does
> every question asked on its way to running (`AskAboutTheOffer` writes it
> onto a `needs_values` question too). Both `_say_yes_to_it` and
> `_answer_the_question` read it here; the answer path keyed the run on the
> question's own id before (S2 review M6), so a mail that went through a
> question never claimed its own key and another door could start it again.

## `Converse._carry_on`, [line 355](../../../../../../../backend/src/sro/application/chat/converse.py#L355): Note

Code: `said=f"Say yes to run {offered.title}, or no to leave it.",`

> Words pressed under an open should-we question that are neither yes nor no
> ask for one again. They never fall through to be read as a new request.

## `Converse._what_stands`, [line 450](../../../../../../../backend/src/sro/application/chat/converse.py#L450): Docstring

> What stands in this thread, in words, or None when nothing does (F2).
>
> The run first: the last run the thread named, read under this tenant, if it
> still `stands` -- and only for a principal who may see it, the thread's
> opener or the run's starter (invariant 5; F2 round 1, M3). Then an offer
> waiting on a yes, read only for the thread's opener: the offer is theirs,
> and what it holds came from their request or their mail (F2 round 2). A standing question never reaches here: `execute`
> answers under it first.

## `Converse._carry_on`, [line 386](../../../../../../../backend/src/sro/application/chat/converse.py#L386): Comment

Code: `if resolution.about_what_stands and standing:`

> A sentence that named no job while something stood (F2). A ready,
> read-only lookup has already answered above -- a lookup is neither a job
> start nor an explore (F2 round 1, I2). Under a question `execute` routed
> here (`standing`), what they said is kept and `execute` asks the question
> again -- its "I am still waiting on this one" / "Nothing back from … yet" is
> the answer about that question. Otherwise the answer is `_what_stands`,
> said with no decision: a status line changes nothing, and a decision-less
> assistant message is skipped by every reader of "what was last asked"
> (`asked_under`, `_awaiting`), so the offer it describes still stands under
> it.

## `Converse._carry_on`, [line 365](../../../../../../../backend/src/sro/application/chat/converse.py#L365): Comment

Code: `async def something_stands() -> bool:`

> Handed to the resolver rather than worked out here, so the thread's run is
> read only when the sentence named nothing (F2 round 1, M6). Under a
> question `execute` routed here, the answer is already known: it stands.

## `_opened_by_the_caller`, [line 1491](../../../../../../../backend/src/sro/application/chat/converse.py#L1491): Docstring

> A run or a note is written into a thread only by the operator who opened it
> (invariant 5), else a 409 and nothing is written. One rule for `started`,
> `may_start`, `note`, `_said_to_a_run` and `execute` (which catches the 409
> and only tells). Unchecked, B's `POST /threads/{A's}/runs`
> wrote B's run into A's thread: `asked_under` then read B's run, and A's
> bare "yes" -- all the console sends -- no longer pressed A's offer (S1
> round 2).

## `_chained`, [line 1488](../../../../../../../backend/src/sro/application/chat/converse.py#L1488): Note

Code: `return str((asked.decision or {}).get("offer") or asked.id.value)`

> The offer a continuation carries on from: the question's own `offer`, or the
> question itself when it is the fresh offer. Every `needs_values` and `job`
> Converse writes in answer to a question carries it -- `_say_yes_to_it`,
> `_answer_the_question`, `_ask_it_again` -- so `the_request` can follow a run's
> offer back to the words that asked for it and to nothing older (S4 round 1,
> I4). The `resume` of an answered question still names that question (the
> run's unique offer); its `offer` leads back from there.

## `Converse.execute`, [line 184](../../../../../../../backend/src/sro/application/chat/converse.py#L184): Note

Code: `run_asks = asked_under(said_before, answering)`

> A line said under a run's open `recipient` or `mail_body` question is that
> question's answer (S4 round 1, I2). The panel and the console both say it
> through this door, so neither needs an answer box: the question they already
> show takes the next line typed under it. Only while the run still asks that
> very question (`_open_in_words`); a line after it closed is an ordinary line.

## `Converse._answer_the_run`, [line 276](../../../../../../../backend/src/sro/application/chat/converse.py#L276): Note

Code: `await answer.execute(`

> The operator's line is kept first, then handed to `AnswerRun` -- found by the
> `run_asks` message's own question id, a compare-and-set, only the starter --
> which on the draft path redrafts before this returns. A refusal (not an
> address, empty, too long, already answered) is said back and the question
> stands.

## `_Closed`, [line 99](../../../../../../../backend/src/sro/application/chat/converse.py#L99): Docstring

> The question a yes (or an answer) was about closed between the first read
> and the write that answers it: another press, a typed yes beside it, a
> second panel. Raised inside the start's transaction, so the run it would
> have claimed is rolled back with it, and the caller is told `K_CLOSED`.

## `Converse._start_it`, [line 630](../../../../../../../backend/src/sro/application/chat/converse.py#L630): Docstring

> A yes, or the last answer to a question, starts the run here -- whichever
> door it came through (S2). Measured on QA 2026-09-28, thread
> thr_fa6507fa: a "yes" typed in the console wrote "Running Create a Customer
> Type now." with `resume: true`, and nothing ran, because only the
> extension's service worker started runs on that decision. The console has
> no extension and a mail has no browser at all.
>
> **Through `StartWorkflowRun.execute`, the start `POST /v1/workflow-runs`
> uses.** Every check lives there and nowhere else: the daily cap, the
> job's required values (F1 `demanded`), its compile, the pinned version
> (X11), the one-run-per-offer unique index, `mail_thread`, `from_step`,
> items, `watched`. The thread's opener (S1) is checked by `execute` before
> this is reached, and the compare-and-set on the question below.
>
> **One commit.** The "Running" message is written by `then`, inside the
> start's own transaction, under the thread's row lock and after the run row
> is inserted: the run and the message naming it commit together or not at
> all. A crash anywhere before the commit leaves neither, and the question
> still open for the next yes; a closed question raises `_Closed` there and
> rolls the run back. Two yeses at once: one takes the offer's unique index,
> the other is refused by it or finds the question closed, so one run and
> one "Running" (tested on Postgres). The run is handed to its executor
> only after the commit, as the route does; the attempt is recorded after
> it, as "start a job from chat" (`_attempted`).
>
> **Refused, it says why.** A refusal (the offer already started a run, no
> connected browser, the cap, a missing value) writes "Nothing was started:
> <why>." with the same `job` decision minus `resume` -- the offer stands
> again, with its values and its `offer` key, so a later yes retries it and
> is still one run. Never a "Running" without a run.
>
> **Where it runs: whatever executor the tenant uses** (controller ruling,
> S2 round 1). `device_id=None` and the start picks it: a Steel tenant runs
> on Steel; a mail-only job on any other tenant runs on the Gmail tool with
> no browser; anything else runs live and watched in the starter's own
> connected browser (`StartWorkflowRun._their_browser`), which is where the
> deleted `resumeTheJob` ran it -- `live=True, allow_focus=True`. Only when
> none of those exists is the thread told "Nothing was started: none of
> your browsers is connected." QA's greyorange is not on Steel, and its
> "Compose and Send Email" is the test.
>
> **Handed on, not awaited.** A run in a browser is driven by `perform` for
> its whole length, and a mail job's `perform` makes the draft's model
> call; awaited here, the operator's "yes" would hang for minutes. It is
> spawned (`Container.pursuits.spawn`) exactly as the press route does, and
> `perform` closes the row itself on any failure. A Steel handoff is quick
> and its answer matters, so it is awaited: `start_on_steel` returning
> False is `_did_not_start`.

## `Converse._did_not_start`, [line 703](../../../../../../../backend/src/sro/application/chat/converse.py#L703): Docstring

> The Steel handoff failed after the commit (S2 review I1): `start_on_steel`
> has already closed the run as failed, so the "Running" line in the thread
> is stale. Handing off before the commit would reopen "a run without its
> message", so instead one more assistant message is appended under the
> thread's row lock -- the thread is append-only (invariant 9), so this
> supersedes "Running" rather than editing it. It names the run (`run_id`
> on a `note`), so `last_run`, `_what_stands` and the ledger read the failed
> run, and it says to ask again: the failed run holds the offer's unique
> key, so a second yes on the same offer would only be told it is closed.

## `Converse._attempted`, [line 732](../../../../../../../backend/src/sro/application/chat/converse.py#L732): Docstring

> A chat start records its attempt as the mail door's does ("start a job
> from a mail"): done with the run, refused with why, failed with why. Before
> S2 the extension's own press recorded a chat yes as "press a job"; the
> backend starting it recorded nothing (S2 review M3). The thread route still
> records "say something in a conversation" beside it.

## `Converse._closed`, [line 751](../../../../../../../backend/src/sro/application/chat/converse.py#L751): Docstring

> `K_CLOSED`, carrying the run this offer already started when there is one
> (S2 review M5). The yes that lost a race to another panel's is otherwise
> told only that the question closed, and that panel never learns which run
> to watch. A press that found the question closed before it reached here
> (`execute`'s own check) names nothing; the panel's thread refresh
> (`watchTheRunIn`) finds the run for it.
