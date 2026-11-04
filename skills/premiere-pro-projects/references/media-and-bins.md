# Project panel: bins, items, MasterClips and Media

Recipes for the project panel and media. The rules are in spec [§6](spec/06-project-panel.md#6-project-panel-bins-project-items-master-clips-media), with IDs in [§2.4](spec/02-document-structure.md#24-allocating-identities) and the object graph in [§4](spec/04-object-graph-and-project.md#4-object-graph); each is proven on the steps it cites ([§0](spec/README.md#0-conventions)). The steps import nine media files (MP4, PNG, JPEG, WAV) and a .txt (00→01), and make a bin and move clips into it (01→02). ClassIDs and fields: [`prproj-classes.md`](prproj-classes.md). `{ID}` = a new ObjectID (max+1), `{UID}` = a new uuid4, `{GUID}` = a new uuid4 as text, `{NODE}` = `Project/NextID`, then increment `NextID`.

## Tree

```
RootProjectItem "Root Bin" (Node ID 1000000)
  ProjectItemContainer/Items/Item Index=i ObjectURef → BinProjectItem | ClipProjectItem | FileProjectItem
BinProjectItem → ProjectItemContainer/Items → more bins or items
ClipProjectItem → MasterClip ObjectURef
```

- Membership lives only in the parent's `Items` list; a child has no parent pointer. Every ClipProjectItem appears in exactly one `Items` list (spec [§6](spec/06-project-panel.md#6-project-panel-bins-project-items-master-clips-media), item 1). The root holds items directly: step 01 imports into it.
- A bin made with New Bin has no `Node/ID` (spec [§2.4](spec/02-document-structure.md#24-allocating-identities)), so leave the `<ID>` out:

```xml
	<BinProjectItem ObjectUID="{UID}" ClassID="dbfd6653-24da-480e-a35e-ba45e9504e4b" Version="1">
		<ProjectItem Version="1">
			<Node Version="1">
				<Properties Version="1">
					<Column.PropertyText.Label>BE.Prefs.LabelColors.7</Column.PropertyText.Label>
				</Properties>
				<ID>{NODE}</ID>                       <!-- optional; Premiere's New Bin writes none -->
			</Node>
			<Name>sfx</Name>
		</ProjectItem>
		<ProjectItemContainer Version="1">
			<Items Version="1">
				<Item Index="0" ObjectURef="{CLIP_PROJECT_ITEM_UID}"/>
			</Items>
		</ProjectItemContainer>
	</BinProjectItem>
```

- `Node/Properties` keys such as `project.icon.view.grid.order`, `project.freeform.view.bin.*`, `ProjectViewState.ID` and `list.view.expanded.state.*` are panel view state. Premiere rewrites `project.icon.view.grid.order` when items move (spec §6, item 1).
- An **empty bin** has an empty `ProjectItemContainer` and no `Items` element [O: step 00 #panel.empty-bin-no-items].

## ClipProjectItem

```xml
	<ClipProjectItem ObjectUID="{UID}" ClassID="cb4e0ed7-aca1-4171-8525-e3658dec06dd" Version="1">
		<ProjectItem Version="1">
			<Node Version="1">
				<Properties Version="1">
					<Column.PropertyText.Label>BE.Prefs.LabelColors.2</Column.PropertyText.Label>
				</Properties>
			</Node>
			<Name>sfx-pop.wav</Name>
		</ProjectItem>
		<MasterClip ObjectURef="{MASTERCLIP_UID}"/>
	</ClipProjectItem>
```

- There's no item type field: an item is a **sequence** when its MasterClip's clips have a `*SequenceSource`, **media** otherwise [O: steps 03–23 #panel.sequence-item].
- **The panel shows `ProjectItem/Name`**; track items show `SubClip/Name` (spec [§9.1](spec/09-track-items-and-links.md#91-anatomy)).

## FileProjectItem (non-media files)

A file Premiere can't play (here `interview.txt`) imports as a `FileProjectItem`, with no MasterClip, Media or `RelativePath`: a name and an absolute `FullPath`, listed in a bin's `Items` like any other item [O: steps 00→01 #panel.file-project-item].

```xml
	<FileProjectItem ObjectUID="{UID}" ClassID="b28f14fe-793f-45be-bb28-fb82644995f4" Version="1">
		<ProjectItem Version="1">
			<Node Version="1">
				<Properties Version="1">
					<Column.PropertyText.Label>BE.Prefs.LabelColors.Unknown</Column.PropertyText.Label>
				</Properties>
			</Node>
			<Name>interview.txt</Name>
		</ProjectItem>
		<FullPath>/abs/path/interview.txt</FullPath>
	</FileProjectItem>
```

## MasterClip

```xml
	<MasterClip ObjectUID="{UID}" ClassID="fb11c33a-b0a9-4465-aa94-b6d5db2628cf" Version="12">
		<Node Version="1">                     <!-- only once placed in a sequence; see Node ID below -->
			<ID>{NODE}</ID>
		</Node>
		<LoggingInfo ObjectRef="{LOG}"/>
		<AudioComponentChains Version="1">
			<AudioComponentChain Index="0" ObjectRef="{ACHAIN}"/>
		</AudioComponentChains>
		<Clips Version="1">
			<Clip Index="0" ObjectRef="{VIDEOCLIP_OR_AUDIOCLIP}"/>
		</Clips>
		<AudioClipChannelGroups ObjectRef="{CCGV}"/>
		<Name>sfx-pop.wav</Name>
		<DefMappingID>{GUID}</DefMappingID>
		<MasterClipChangeVersion>1</MasterClipChangeVersion>
	</MasterClip>
```

- **Clips**, in order: for media the VideoClip (if any), then the AudioClip; for a sequence the AudioClip, then the VideoClip; then a TranscriptClip once Speech to Text has run [O: steps 01–23 #panel.masterclip-clips-order].
- **Node ID:** Premiere's import gives a media MasterClip none; it takes `Project/NextID` the first time the clip is placed in a sequence [O: steps 00→01, 02→03, 04→05 #doc.node-id-on-placement]. `place` does the same.
- `MasterClipChangeVersion` is an edit counter; on a sequence's MasterClip Premiere raises it on every edit (spec [§7.4](spec/07-sequences.md#74-length)).
- `DefMappingID`: one value is shared by six MasterClips in step 01 [O: step 01 #doc.defmappingid-shared].
- The MasterClip's `AudioComponentChain` (clip volume defaults, an empty chain) and its three-level channel map, as imported in step 01:

```xml
	<AudioComponentChain ObjectID="{ACHAIN}" ClassID="3cb131d1-d3c0-47ae-a19a-bdf75ea11674" Version="4">
		<DefaultVol>true</DefaultVol>
		<DefaultVolumeComponentID>1</DefaultVolumeComponentID>
		<DefaultChannelVolumeComponentID>2</DefaultChannelVolumeComponentID>
		<ComponentChain Version="3">
		</ComponentChain>
		<AudioChannelLayout>[{"channellabel":100},{"channellabel":101}]</AudioChannelLayout>
		<ChannelType>1</ChannelType>
	</AudioComponentChain>
```

```xml
	<ClipChannelGroupVectorSerializer ObjectID="{CCGV}" ClassID="a3127a8c-95d4-456e-a7f5-171b3f922426" Version="1">
		<ClipChannelVectors Version="1">
			<ClipChannelVectorItem Index="0" ObjectRef="{CCV}"/>
		</ClipChannelVectors>
	</ClipChannelGroupVectorSerializer>
	<ClipChannelVectorSerializer ObjectID="{CCV}" ClassID="333d203b-3a53-4195-8894-fc7523ff3dc7" Version="1">
		<ClipChannels Version="1">
			<ClipChannelItem Index="0" ObjectRef="{CC0}"/>
			<ClipChannelItem Index="1" ObjectRef="{CC1}"/>   <!-- one per channel -->
		</ClipChannels>
		<ChannelType>1</ChannelType>
	</ClipChannelVectorSerializer>
	<ClipChannelSerializer ObjectID="{CC0}" ClassID="5c89aa7a-89a6-4483-becd-f2b1def42316" Version="1">
		<mSourceChannelIndex>0</mSourceChannelIndex>          <!-- 1 for CC1 -->
		<SourceClipIndex>0</SourceClipIndex>
	</ClipChannelSerializer>
```

## ClipLoggingInfo

```xml
	<ClipLoggingInfo ObjectID="{LOG}" ClassID="77ab7fdd-dcdf-465d-9906-7a330ca1e738" Version="10">
		<CaptureMode>1</CaptureMode>
		<ClipName>sfx-pop.wav</ClipName>
		<MediaInPoint>0</MediaInPoint>
		<MediaOutPoint>{DURATION}</MediaOutPoint>
		<MediaFrameRate>5292000</MediaFrameRate>
		<TimecodeFormat>200</TimecodeFormat>
	</ClipLoggingInfo>
```

Values per media kind, as Premiere's import wrote them in step 01: [`prproj-classes.md`](prproj-classes.md#cliplogginginfo). A sequence's ClipLoggingInfo holds only `ClipName`.

## Clips inside a MasterClip

```xml
	<VideoClip ObjectID="{VC}" ClassID="9308dbef-2440-4acb-9ab2-953b9a4e82ec" Version="11">
		<Clip Version="18">
			<Node Version="1">
				<Properties Version="1">
					<asl.clip.label.name>BE.Prefs.LabelColors.3</asl.clip.label.name>
				</Properties>
			</Node>
			<MarkerOwner Version="1">
				<Markers ObjectRef="{MK}"/>
			</MarkerOwner>
			<Source ObjectRef="{VMS}"/>
			<ClipID>{GUID}</ClipID>
			<InUse>false</InUse>
		</Clip>
	</VideoClip>
	<AudioClip ObjectID="{AC}" ClassID="b8830d03-de02-41ee-84ec-fe566dc70cd9" Version="8">
		<Clip Version="18"> …same; Source → {AMS}… </Clip>
		<SecondaryContents Version="1">
			<SecondaryContentItem Index="0" ObjectRef="{SC0}"/>
			<SecondaryContentItem Index="1" ObjectRef="{SC1}"/>
		</SecondaryContents>
		<AudioChannelLayout>[{"channellabel":100},{"channellabel":101}]</AudioChannelLayout>
	</AudioClip>
	<SecondaryContent ObjectID="{SC0}" ClassID="f9d004b5-cb04-4e2f-af6f-64fadc2c4be9" Version="1">
		<Content ObjectRef="{AMS}"/>
		<ChannelIndex>0</ChannelIndex>
	</SecondaryContent>
	<Markers ObjectID="{MK}" ClassID="bee50706-b524-416c-9f03-b596ce5f6866" Version="4">
		<ByGUID>byGUID</ByGUID>
		<LastMetadataState>00000000-0000-0000-0000-000000000000</LastMetadataState>
		<LastContentState>00000000-0000-0000-0000-000000000000</LastContentState>
	</Markers>
```

- Every clip of a media MasterClip, and every timeline clip of that media, points at one shared `Markers` object, created empty at import [O: steps 00→01 #markers.media-owner]. Clips whose source is a sequence have none (spec [§13](spec/13-markers.md#13-markers)).
- On a media clip's Markers, `LastContentState` = the Media's `ContentAndMetadataState` [O: steps 01–23 #markers.media-content-state].
- The TranscriptClip, its DataMediaSource, the transcript Media and the transcript document: see `transcripts-and-captions.md`. Don't create them.

## Sources

```xml
	<VideoMediaSource ObjectID="{VMS}" ClassID="e64ddf74-8fac-4682-8aa8-0e0ca2248949" Version="2">
		<MediaSource Version="4">
			<Content Version="10">
			</Content>
			<Media ObjectURef="{MEDIA_UID}"/>
		</MediaSource>
		<OriginalDuration>{DURATION}</OriginalDuration>
	</VideoMediaSource>
```

- `AudioMediaSource` is the same with ClassID `f588da05-fc2a-4fbc-9383-74d653b379e3`. Each refers to one Media.
- A timeline clip owns its own `VideoClip`/`AudioClip`, whose `Source` is the shared media or sequence source [O: steps 03–23 #graph.timeline-clip-owns-clip]: never clone a source when placing a clip.
- A sequence has one `VideoSequenceSource` and one `AudioSequenceSource`, owned by its MasterClip's clips. Their `OriginalDuration` isn't the sequence's length (spec [§6](spec/06-project-panel.md#6-project-panel-bins-project-items-master-clips-media), item 6, and [§7.4](spec/07-sequences.md#74-length)). Using a sequence as a clip in another (nesting) isn't covered ([§18](spec/18-not-observed.md)).

## Media

`clip-a.mp4` as Premiere imported it (step 01; paths shortened, blob elided):

```xml
	<Media ObjectUID="{UID}" ClassID="7a5c103e-f3ac-4391-b6b4-7cc3d2f9a7ff" Version="30">
		<AudioStream ObjectRef="{AS}"/>
		<VideoStream ObjectRef="{VS}"/>
		<ModificationState Encoding="base64" BinaryHash="…">…</ModificationState>
		<RelativePath>../media/clip-a.mp4</RelativePath>
		<ImplementationID>1fa18bfa-255c-44b1-ad73-56bcd99fceaf</ImplementationID>
		<FileKey>{GUID}</FileKey>
		<ConformedAudioRate>5292000</ConformedAudioRate>
		<ContentAndMetadataState>{GUID}</ContentAndMetadataState>
		<ContentCredentialsInfo>5120</ContentCredentialsInfo>
		<CCManifestLocation>1</CCManifestLocation>
		<CCFileModTime>{TIME}</CCFileModTime>
		<ActualMediaFilePath>/abs/path/media/clip-a.mp4</ActualMediaFilePath>
		<FilePath>/abs/path/media/clip-a.mp4</FilePath>
		<Title>clip-a.mp4</Title>
	</Media>
```

- **Paths:** `FilePath` and `ActualMediaFilePath` are absolute; with `RelativePath` they locate the file, and relinking must change all of them (spec [§6](spec/06-project-panel.md#6-project-panel-bins-project-items-master-clips-media), item 4).
- `RelativePath` is relative to the folder the .prproj was **saved** in and is rewritten on every save; the absolute paths aren't. A .prproj moved by hand keeps the old, now wrong, `RelativePath` until Premiere saves it [O: steps 03→04, 04→05 #panel.relative-path].
- **Probe caches:** Premiere-saved Media of a file always carry `ModificationState`, `ContentAndMetadataState`, `CCFileModTime` and the AudioStream's `ConformedAudioPath`/`PeakFilePath` [O: steps 01–23 #panel.media-probe-caches]. Keep them when editing.
- `ImplementationID` (the importer) is a constant: copy it from a Media of the same kind, never generate one (spec [§2.4](spec/02-document-structure.md#24-allocating-identities)).

### Streams

`clip-a.mp4`'s streams (step 01):

```xml
	<VideoStream ObjectID="{VS}" ClassID="a36e4719-3ec6-4a0c-ab11-8b4aab377aa5" Version="23">
		<Duration>5074805736000</Duration>
		<IgnoreAlpha>true</IgnoreAlpha>
		<CodecType>1635148593</CodecType>
		<OriginalColorSpace>{"baseColorProfile":{…,"colorProfileName":"BT.709,32f,Display-Referred"},"baseProfileType":1}</OriginalColorSpace>
		<FieldTypeIsUncertain>true</FieldTypeIsUncertain>
		<OriginalImageOrientationType>1</OriginalImageOrientationType>
		<FrameRate>10594584000</FrameRate>
		<FrameRect>0,0,1920,1080</FrameRect>
		<AlphaType>3</AlphaType>
	</VideoStream>
	<AudioStream ObjectID="{AS}" ClassID="0b5cf52f-2b85-4863-890b-8844b64ecfe9" Version="8">
		<AudioChannelLayout>[{"channellabel":100},{"channellabel":101}]</AudioChannelLayout>
		<Duration>5074805736000</Duration>
		<SampleType>7</SampleType>
		<ConformedAudioPath>/abs/path/…</ConformedAudioPath>
		<PeakFilePath>/abs/path/…</PeakFilePath>
		<FrameRate>5292000</FrameRate>
	</AudioStream>
```

`VideoStream` holds duration, rate, size, `CodecType` FourCC and alpha; `AudioStream` the duration, channel layout and cache paths; a transcript's Media has a `DataStream` (spec [§6](spec/06-project-panel.md#6-project-panel-bins-project-items-master-clips-media), item 5). Durations are in ticks, 254 016 000 000 per second; FourCCs are big-endian bytes as a decimal integer (spec [§3](spec/03-value-encodings.md#3-value-encodings)).

## What Premiere's import writes

Importing adds the file's whole chain and changes nothing else but the target bin's `Items` and `Project`: 18 top-level objects for video with stereo audio, 9 for video only (including stills), 15 for stereo audio; the MasterClip gets no Node ID and its clips an empty Markers object [O: steps 00→01 #panel.import]. Writing an import by hand isn't covered ([§18](spec/18-not-observed.md)): ask the user to import the file in Premiere, save, and then work on the result.

## Recipes

Global rules (new IDs and GUIDs, targeted string edits, `validate --orig`) are in `object-surgery.md`.

### Create a bin

What Premiere's New Bin writes (steps 01→02):

1. Write a BinProjectItem (skeleton above): new `{UID}`, name, no Node `<ID>`. With no children yet, leave `ProjectItemContainer` empty (no `Items`).
2. Insert it after the last top-level `BinProjectItem`.
3. Append `<Item Index="{n}" ObjectURef="{UID}"/>` to the parent's `Items` (root or another bin), with n = the current count.

### Move an item between bins

Premiere's move of four clips into a new bin edited only the two `Items` lists [O: steps 01→02 #panel.move-item]:

1. Delete its `<Item …ObjectURef="X"/>` line from the old bin and re-index the remaining `Index` values to 0..n-1.
2. Append it to the new bin with Index = count. Create the new bin's `Items` if it has none.
3. Leave the panel view-state keys (`project.icon.view.grid.order`, `project.freeform.view.bin.coordinate`) alone.

### Move the .prproj to another folder

Rewrite every Media's `RelativePath` for the new folder, the way Premiere does on save; leave `FilePath` and `ActualMediaFilePath` (spec [§6](spec/06-project-panel.md#6-project-panel-bins-project-items-master-clips-media), item 4). Step 04 in `fixtures/premiere-pro/steps/` was saved one folder up and shows the difference. `FileProjectItem/FullPath` is absolute and doesn't change.

### Not covered

Renaming items, relinking media to another file, importing media by hand and duplicate imports of one file aren't covered ([§18](spec/18-not-observed.md)). Ask the user to do them in Premiere.

### Don't

- Don't clone a TranscriptClip or transcript Media into a new import.
- Don't reuse another clip's `ClipID`: every one is unique (spec [§2.4](spec/02-document-structure.md#24-allocating-identities)).
- Don't leave a MasterClip without a ClipProjectItem.
- Don't remove an item that track items still use. Check `SubClip/MasterClip` refs first.
